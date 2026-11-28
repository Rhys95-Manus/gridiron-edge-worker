"""PRV-10 training and calibration rows: played player-games, their labels, point-in-time mu for
a season and the PRV-08 gate, on synthetic data only (made-up IDs; no real players or games)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import polars as pl
import pytest

from ge.config import load_params
from ge.pricer_v0.projection import Prv03Fit
from ge.pricer_v0.reasons import PricerUnpriced
from ge.pricer_v0.training import (
    LABELS_SCHEMA,
    MU_SCHEMA,
    GameInputs,
    labels_from,
    read_schedule,
    season_mu,
    training_rows,
    with_availability,
)
from ge.store.holdout import HoldoutReadError
from ge.store.snapshot import FF_OPPORTUNITY_COLUMNS

FIT = Prv03Fit(
    window="S2022",
    usage_half_life=6.0,
    k={"receptions": 40.0, "receiving_yards": 40.0, "rushing_yards": 40.0},
    efficiency_half_life=8.0,
)
UTC = dt.UTC


def _ff(rows: list[dict[str, Any]]) -> pl.DataFrame:
    schema = {
        c: pl.Utf8 if c in ("game_id", "player_id", "posteam", "position") else pl.Float64
        for c in FF_OPPORTUNITY_COLUMNS
    }
    base = {c: 0.0 for c in FF_OPPORTUNITY_COLUMNS}
    return pl.DataFrame([base | r for r in rows], schema=schema)


def _played(rows: list[tuple[str, str, str]]) -> pl.DataFrame:
    return pl.DataFrame(
        [{"gsis_id": p, "team": t, "game_id": g} for p, t, g in rows],
        schema={"gsis_id": pl.Utf8, "team": pl.Utf8, "game_id": pl.Utf8},
    )


# ---- labels (PRV-10: played player-games; no ff row counts the stat as 0) ----


def test_labels_take_the_ff_actuals_of_every_played_player_game() -> None:
    g = "2022_05_TMA_TMB"
    ff = _ff(
        [
            {
                "game_id": g,
                "player_id": "A1",
                "posteam": "TMA",
                "position": "WR",
                "receptions": 4.0,
                "rec_yards_gained": 51.0,
                "rush_yards_gained": -2.0,
                "rush_attempt": 1.0,
            }
        ]
    )
    out = labels_from(_played([("A1", "TMA", g)]), ff, 2022)
    assert out.schema == pl.Schema(LABELS_SCHEMA)
    row = out.row(0, named=True)
    assert row == {
        "game_id": g,
        "team": "TMA",
        "gsis_id": "A1",
        "has_ff_row": True,
        "receptions": 4.0,
        "receiving_yards": 51.0,
        "rushing_yards": -2.0,
        "carries": 1.0,
    }


def test_a_played_game_with_no_ff_row_counts_every_stat_as_zero() -> None:
    g = "2022_05_TMA_TMB"
    out = labels_from(_played([("A1", "TMA", g)]), _ff([]), 2022)
    row = out.row(0, named=True)
    assert row["has_ff_row"] is False
    assert [row[c] for c in ("receptions", "receiving_yards", "rushing_yards", "carries")] == [
        0.0
    ] * 4


def test_null_actuals_count_as_zero() -> None:
    g = "2022_05_TMA_TMB"
    ff = _ff([{"game_id": g, "player_id": "A1", "posteam": "TMA", "position": "WR"}]).with_columns(
        pl.lit(None, dtype=pl.Float64).alias("rec_yards_gained")
    )
    row = labels_from(_played([("A1", "TMA", g)]), ff, 2022).row(0, named=True)
    assert row["has_ff_row"] is True and row["receiving_yards"] == 0.0


def test_ff_rows_of_players_who_did_not_play_are_not_labels() -> None:
    g = "2022_05_TMA_TMB"
    ff = _ff(
        [
            {"game_id": g, "player_id": "A1", "posteam": "TMA", "receptions": 2.0},
            {"game_id": g, "player_id": "A2", "posteam": "TMA", "receptions": 1.0},
        ]
    )
    out = labels_from(_played([("A1", "TMA", g)]), ff, 2022)
    assert out["gsis_id"].to_list() == ["A1"]


def test_labels_keep_only_the_season_and_ignore_null_ff_players() -> None:
    g, old = "2022_05_TMA_TMB", "2021_05_TMA_TMB"
    ff = _ff(
        [
            {"game_id": g, "player_id": None, "posteam": "TMA", "receptions": 9.0},
            {"game_id": g, "player_id": None, "posteam": "TMA", "receptions": 9.0},
            {"game_id": old, "player_id": "A1", "posteam": "TMA", "receptions": 7.0},
        ]
    )
    out = labels_from(_played([("A1", "TMA", g), ("A1", "TMA", old)]), ff, 2022)
    assert out["game_id"].to_list() == [g]
    assert out["receptions"].to_list() == [0.0]


def test_two_ff_rows_for_one_played_player_game_stop() -> None:
    g = "2022_05_TMA_TMB"
    ff = _ff(
        [
            {"game_id": g, "player_id": "A1", "posteam": "TMA"},
            {"game_id": g, "player_id": "A1", "posteam": "TMA"},
        ]
    )
    with pytest.raises(ValueError, match="PRV-10"):
        labels_from(_played([("A1", "TMA", g)]), ff, 2022)


def test_labels_do_not_depend_on_row_order() -> None:
    g1, g2 = "2022_05_TMA_TMB", "2022_06_TMA_TMC"
    played = _played([("B1", "TMB", g1), ("A1", "TMA", g2), ("A1", "TMA", g1)])
    ff = _ff(
        [
            {"game_id": g1, "player_id": "A1", "posteam": "TMA", "receptions": 1.0},
            {"game_id": g2, "player_id": "A1", "posteam": "TMA", "receptions": 2.0},
        ]
    )
    a = labels_from(played, ff, 2022)
    b = labels_from(played.reverse(), ff.reverse(), 2022)
    assert a.equals(b)
    assert a.select("game_id", "team", "gsis_id").rows() == [
        (g1, "TMA", "A1"),
        (g1, "TMB", "B1"),
        (g2, "TMA", "A1"),
    ]


# ---- PRV-08 on mu rows ----


def _mu_rows(players: list[tuple[str, str]]) -> pl.DataFrame:
    rows = [
        {
            "game_id": "2022_05_TMA_TMB",
            "as_of": dt.datetime(2022, 10, 8, tzinfo=UTC),
            "team": t,
            "gsis_id": p,
            "stat": "receptions",
            "n_games": 4,
            "group": "WR",
            "e": 3.0,
            "m": 0.0,
            "g": 0.0,
            "g_n_eff": 4.0,
            "mu": 3.0,
            "carries_mean": 0.0,
            "reason": None,
            "centring_label": "c",
            "fit_window": "S2022",
        }
        for t, p in players
    ]
    return pl.DataFrame(rows, schema=MU_SCHEMA)


def _inj(rows: list[tuple[str, str, str | None]], week: int = 5) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {"season": 2022, "week": week, "team": t, "gsis_id": p, "report_status": s}
            for t, p, s in rows
        ],
        schema={
            "season": pl.Int64,
            "week": pl.Int64,
            "team": pl.Utf8,
            "gsis_id": pl.Utf8,
            "report_status": pl.Utf8,
        },
    )


def test_with_availability_adds_prv08_for_each_player() -> None:
    mu = _mu_rows([("TMA", "A1"), ("TMA", "A2"), ("TMB", "B1"), ("TMB", "B2")])
    inj = _inj(
        [
            ("TMA", "A1", "Doubtful"),
            ("TMA", "A2", "Questionable"),
            ("TMB", "B1", "Probable"),
            ("TMA", "A9", "Out"),
            ("TMB", "B2", "Out"),
        ]
    )
    out = with_availability(mu, inj, season=2022, week=5)
    got = {
        r["gsis_id"]: (r["status_seen"], r["availability_flag"], r["availability_reason"])
        for r in out.iter_rows(named=True)
    }
    assert got == {
        "A1": ("Doubtful", None, PricerUnpriced.DOUBTFUL.value),
        "A2": ("Questionable", "questionable", None),
        "B1": ("Probable", None, PricerUnpriced.INJURY_STATUS_UNCLEAR.value),
        "B2": ("Out", None, PricerUnpriced.OUT.value),
    }
    assert out.select(mu.columns).equals(mu)


def test_with_availability_reads_only_the_target_week() -> None:
    mu = _mu_rows([("TMA", "A1")])
    inj = pl.concat([_inj([("TMA", "A1", "Out")], week=4), _inj([("TMA", "A2", "Out")], week=5)])
    row = with_availability(mu, inj, season=2022, week=5).row(0, named=True)
    assert row["status_seen"] == "not_listed" and row["availability_reason"] is None
    assert row["availability_flag"] is None  # TMA's week-5 report is in (A2 Out)


# ---- season mu (PRV-10: point-in-time mu at kickoff - 24 h for every game) ----


def _schedule() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["2022_02_TMA_TMB", "2022_01_TMA_TMB"],
            "kickoff_utc": [
                dt.datetime(2022, 9, 18, 17, tzinfo=UTC),
                dt.datetime(2022, 9, 11, 17, tzinfo=UTC),
            ],
            "home_team": ["TMB", "TMB"],
            "away_team": ["TMA", "TMA"],
            "week": [2, 1],
        },
        schema={
            "game_id": pl.Utf8,
            "kickoff_utc": pl.Datetime("us", "UTC"),
            "home_team": pl.Utf8,
            "away_team": pl.Utf8,
            "week": pl.Int64,
        },
    )


def test_season_mu_opens_each_game_at_kickoff_minus_24h_in_kickoff_order() -> None:
    hours = load_params().backtest.bt_01_decision_hours_before_kickoff.value
    seen: list[tuple[str, dt.datetime]] = []
    empty_games = pl.DataFrame(
        schema={"team": pl.Utf8, "game_id": pl.Utf8, "week": pl.Int64, "g": pl.Float64}
    )

    def open_game(game_id: str, as_of: dt.datetime) -> GameInputs:
        seen.append((game_id, as_of))
        return GameInputs(ff=_ff([]), games=empty_games, injuries=_inj([]), week=0)

    out = season_mu(2022, _schedule(), fit=FIT, open_game=open_game)
    assert seen == [
        ("2022_01_TMA_TMB", dt.datetime(2022, 9, 11, 17, tzinfo=UTC) - dt.timedelta(hours=hours)),
        ("2022_02_TMA_TMB", dt.datetime(2022, 9, 18, 17, tzinfo=UTC) - dt.timedelta(hours=hours)),
    ]
    assert out.height == 0
    assert {"status_seen", "availability_flag", "availability_reason"} <= set(out.columns)


def test_season_mu_prices_both_teams_with_the_window_fit_and_prv08() -> None:
    weeks = (1, 2, 3)
    games = pl.DataFrame(
        [
            {"team": t, "game_id": f"2022_{w:02d}_TMA_TMB", "week": w, "g": float(i)}
            for t in ("TMA", "TMB")
            for i, w in enumerate(sorted(weeks, reverse=True))
        ],
        schema={"team": pl.Utf8, "game_id": pl.Utf8, "week": pl.Int64, "g": pl.Float64},
    )
    ff = _ff(
        [
            {
                "game_id": f"2022_{w:02d}_TMA_TMB",
                "player_id": p,
                "posteam": t,
                "position": "WR",
                "rec_attempt": 2.0,
                "receptions": 1.0,
                "receptions_exp": 1.0,
            }
            for w in weeks
            for p, t in (("A1", "TMA"), ("B1", "TMB"))
        ]
    )
    sched = pl.DataFrame(
        {
            "game_id": ["2022_04_TMA_TMB"],
            "kickoff_utc": [dt.datetime(2022, 10, 2, 17, tzinfo=UTC)],
            "home_team": ["TMB"],
            "away_team": ["TMA"],
            "week": [4],
        },
        schema=_schedule().schema,
    )

    def open_game(game_id: str, as_of: dt.datetime) -> GameInputs:
        return GameInputs(ff=ff, games=games, injuries=_inj([("TMB", "B1", "Out")], 4), week=4)

    out = season_mu(2022, sched, fit=FIT, open_game=open_game)
    assert out.height == 2 * 3
    assert set(out["fit_window"].to_list()) == {"S2022"}
    a1 = out.filter((pl.col("gsis_id") == "A1") & (pl.col("stat") == "receptions")).row(
        0, named=True
    )
    assert a1["mu"] == pytest.approx(1.0) and a1["availability_reason"] is None
    b1 = out.filter(pl.col("gsis_id") == "B1")["availability_reason"].unique().to_list()
    assert b1 == [PricerUnpriced.OUT.value]


def test_season_mu_refuses_a_game_from_another_season() -> None:
    bad = _schedule().with_columns(pl.lit("2021_01_TMA_TMB").alias("game_id"))
    with pytest.raises(ValueError, match="PRV-10"):
        season_mu(2022, bad, fit=FIT, open_game=lambda g, a: pytest.fail("opened"))


def test_read_schedule_refuses_the_holdout_before_opening(tmp_path: Path) -> None:
    d = tmp_path / "schedules" / "season=2025" / "pulled_at=20260101T000000Z"
    d.mkdir(parents=True)
    (d / "part.parquet").write_bytes(b"not parquet: must never be opened")
    with pytest.raises(HoldoutReadError):
        read_schedule(2025, root=tmp_path)


# ---- training rows ----


def test_training_rows_are_priced_available_played_player_games() -> None:
    mu = with_availability(
        _mu_rows([("TMA", "A1"), ("TMA", "A2"), ("TMA", "A3"), ("TMA", "A4")]),
        _inj([("TMA", "A3", "Doubtful")]),
        season=2022,
        week=5,
    ).with_columns(
        pl.when(pl.col("gsis_id") == "A2")
        .then(pl.lit(PricerUnpriced.MU_NOT_POSITIVE.value))
        .otherwise(pl.col("reason"))
        .alias("reason")
    )
    g = "2022_05_TMA_TMB"
    labels = labels_from(
        _played([("A1", "TMA", g), ("A2", "TMA", g), ("A3", "TMA", g), ("A5", "TMA", g)]),
        _ff([{"game_id": g, "player_id": "A1", "posteam": "TMA", "receptions": 6.0}]),
        2022,
    )
    out = training_rows(mu, labels, "receptions")
    # A2 unpriced (PRV-03), A3 Doubtful (PRV-08), A4 did not play, A5 has no mu
    assert out["gsis_id"].to_list() == ["A1"]
    row = out.row(0, named=True)
    assert row["actual"] == 6.0 and row["mu"] == 3.0 and row["has_ff_row"] is True


def test_training_rows_keep_a_played_game_with_no_ff_row_as_zero() -> None:
    g = "2022_05_TMA_TMB"
    mu = with_availability(_mu_rows([("TMA", "A1")]), _inj([]), season=2022, week=5)
    labels = labels_from(_played([("A1", "TMA", g)]), _ff([]), 2022)
    row = training_rows(mu, labels, "receptions").row(0, named=True)
    assert row["actual"] == 0.0 and row["has_ff_row"] is False


def test_training_rows_need_the_same_team() -> None:
    g = "2022_05_TMA_TMB"
    mu = with_availability(_mu_rows([("TMA", "A1")]), _inj([]), season=2022, week=5)
    labels = labels_from(_played([("A1", "TMB", g)]), _ff([]), 2022)
    assert training_rows(mu, labels, "receptions").height == 0
