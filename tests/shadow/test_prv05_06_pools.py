"""PRV-05/06 compound-model yard pools and the PRV-10 training windows, on synthetic data only
(made-up IDs; no real players or games)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import polars as pl
import pytest

from ge.pricer_v0.projection import Centring, Prv03Fit
from ge.pricer_v0.reasons import PricerUnpriced
from ge.pricer_v0.training import (
    POOL_PBP_COLUMNS,
    game_mu,
    pricer_window,
    read_window_frames,
    yards_pools,
)
from ge.store.holdout import HoldoutReadError
from ge.store.snapshot import FF_OPPORTUNITY_COLUMNS

# ---- PRV-10 windows ----


def test_walk_forward_windows_train_on_2021_to_s_minus_1() -> None:
    assert pricer_window("S2022").seasons == (2021,)
    assert pricer_window("S2023").seasons == (2021, 2022)
    assert pricer_window("S2024").seasons == (2021, 2022, 2023)
    assert pricer_window("S2024").test_season == 2024


def test_live_window_is_2021_to_2024() -> None:
    w = pricer_window("live")
    assert w.seasons == (2021, 2022, 2023, 2024) and w.test_season is None


@pytest.mark.parametrize("name", ["S2021", "S2025", "S2026", "S2020", "x", "S20x2"])
def test_only_scored_seasons_and_live_are_windows(name: str) -> None:
    with pytest.raises(ValueError):
        pricer_window(name)


def test_window_refuses_the_holdout_and_its_test_season() -> None:
    w = pricer_window("S2023")
    with pytest.raises(HoldoutReadError):
        w.check_read(2025)
    with pytest.raises(HoldoutReadError):
        w.check_read(2023)


# ---- reading ----


def _write(root: Path, ds: str, season: int, df: pl.DataFrame | None, stamp: str) -> None:
    d = root / ds / f"season={season}" / f"pulled_at={stamp}"
    d.mkdir(parents=True)
    if df is None:
        (d / "part.parquet").write_bytes(b"not parquet: must never be opened")
    else:
        df.write_parquet(d / "part.parquet")


def _pbp(rows: list[dict[str, Any]]) -> pl.DataFrame:
    schema: dict[str, Any] = {
        "game_id": pl.Utf8,
        "play_id": pl.Float64,
        "complete_pass": pl.Float64,
        "receiver_player_id": pl.Utf8,
        "rush_attempt": pl.Float64,
        "rusher_player_id": pl.Utf8,
        "two_point_attempt": pl.Float64,
        "yards_gained": pl.Float64,
    }
    assert set(schema) == set(POOL_PBP_COLUMNS)
    full = [
        {
            "complete_pass": 0.0,
            "receiver_player_id": None,
            "rush_attempt": 0.0,
            "rusher_player_id": None,
            "two_point_attempt": 0.0,
            "yards_gained": 0.0,
        }
        | r
        for r in rows
    ]
    return pl.DataFrame(full, schema=schema)


def _ff(rows: list[tuple[str, str, str | None]]) -> pl.DataFrame:
    schema = {
        c: pl.Utf8 if c in ("game_id", "player_id", "posteam", "position") else pl.Float64
        for c in FF_OPPORTUNITY_COLUMNS
    }
    full = [
        {c: 0.0 for c in FF_OPPORTUNITY_COLUMNS}
        | {"game_id": g, "player_id": p, "posteam": "TMA", "position": pos}
        for g, p, pos in rows
    ]
    return pl.DataFrame(full, schema=schema)


def test_read_window_frames_opens_only_the_window_seasons(tmp_path: Path) -> None:
    for s in (2021, 2022):
        _write(
            tmp_path,
            "pbp",
            s,
            _pbp([{"game_id": f"{s}_01_TMA_TMB", "play_id": 1.0}]),
            "20260101T000000Z",
        )
        _write(
            tmp_path,
            "ff_opportunity",
            s,
            _ff([(f"{s}_01_TMA_TMB", "P1", "WR")]),
            "20260101T000000Z",
        )
    for ds in ("pbp", "ff_opportunity"):
        _write(tmp_path, ds, 2023, None, "20260101T000000Z")
        _write(tmp_path, ds, 2025, None, "20260101T000000Z")
    pbp, ff = read_window_frames(pricer_window("S2022"), root=tmp_path)
    assert pbp["game_id"].to_list() == ["2021_01_TMA_TMB"]
    assert ff["game_id"].to_list() == ["2021_01_TMA_TMB"]
    pbp2, _ = read_window_frames(pricer_window("S2023"), root=tmp_path)
    assert sorted(pbp2["game_id"].to_list()) == ["2021_01_TMA_TMB", "2022_01_TMA_TMB"]


def test_read_window_frames_uses_the_latest_pull(tmp_path: Path) -> None:
    g = "2021_01_TMA_TMB"
    _write(tmp_path, "pbp", 2021, _pbp([{"game_id": g, "play_id": 1.0}]), "20260101T000000Z")
    _write(tmp_path, "pbp", 2021, _pbp([{"game_id": g, "play_id": 2.0}]), "20260201T000000Z")
    _write(tmp_path, "ff_opportunity", 2021, _ff([(g, "P1", "WR")]), "20260101T000000Z")
    pbp, _ = read_window_frames(pricer_window("S2022"), root=tmp_path)
    assert pbp["play_id"].to_list() == [2.0]


def test_a_missing_season_stops(tmp_path: Path) -> None:
    _write(tmp_path, "pbp", 2021, _pbp([]), "20260101T000000Z")
    with pytest.raises(FileNotFoundError):
        read_window_frames(pricer_window("S2022"), root=tmp_path)


# ---- pools ----

G1, G2 = "2021_01_TMA_TMB", "2021_02_TMA_TMC"


def test_per_reception_pool_uses_completions_and_that_games_group() -> None:
    pbp = _pbp(
        [
            {
                "game_id": G1,
                "play_id": 10.0,
                "complete_pass": 1.0,
                "receiver_player_id": "P1",
                "yards_gained": 12.0,
            },
            {
                "game_id": G1,
                "play_id": 5.0,
                "complete_pass": 1.0,
                "receiver_player_id": "P1",
                "yards_gained": -3.0,
            },
            {
                "game_id": G1,
                "play_id": 20.0,
                "complete_pass": 0.0,
                "receiver_player_id": "P1",
                "yards_gained": 0.0,
            },
            {
                "game_id": G2,
                "play_id": 7.0,
                "complete_pass": 1.0,
                "receiver_player_id": "P1",
                "yards_gained": 30.0,
            },
            {
                "game_id": G1,
                "play_id": 30.0,
                "complete_pass": 1.0,
                "receiver_player_id": "P2",
                "yards_gained": 8.0,
            },
        ]
    )
    # P1 is a WR in G1 and a TE in G2; P2 has a null position (group Other)
    ff = _ff([(G1, "P1", "WR"), (G2, "P1", "TE"), (G1, "P2", None)])
    pools = yards_pools(pbp, ff, pricer_window("S2022"))
    # canonical order: game_id, then play_id
    assert pools.per_reception == {"WR": (-3.0, 12.0), "TE": (30.0,), "Other": (8.0,)}
    assert pools.dropped_receptions == 0


def test_per_carry_pool_includes_every_rush_attempt_with_negatives() -> None:
    pbp = _pbp(
        [
            {
                "game_id": G1,
                "play_id": 1.0,
                "rush_attempt": 1.0,
                "rusher_player_id": "Q1",
                "yards_gained": 9.0,
            },
            {
                "game_id": G1,
                "play_id": 2.0,
                "rush_attempt": 1.0,
                "rusher_player_id": "Q1",
                "yards_gained": -1.0,
            },
            {
                "game_id": G1,
                "play_id": 3.0,
                "rush_attempt": 1.0,
                "rusher_player_id": "R1",
                "yards_gained": -4.0,
            },
            {
                "game_id": G1,
                "play_id": 4.0,
                "rush_attempt": 0.0,
                "rusher_player_id": "R1",
                "yards_gained": 50.0,
            },
        ]
    )
    ff = _ff([(G1, "Q1", "QB"), (G1, "R1", "RB")])
    pools = yards_pools(pbp, ff, pricer_window("S2022"))
    assert pools.per_carry == {"QB": (9.0, -1.0), "RB": (-4.0,)}
    assert pools.per_reception == {}


def test_two_point_tries_are_left_out_of_both_pools() -> None:
    pbp = _pbp(
        [
            {
                "game_id": G1,
                "play_id": 1.0,
                "rush_attempt": 1.0,
                "rusher_player_id": "R1",
                "yards_gained": 2.0,
                "two_point_attempt": 1.0,
            },
            {
                "game_id": G1,
                "play_id": 2.0,
                "complete_pass": 1.0,
                "receiver_player_id": "R1",
                "yards_gained": 2.0,
                "two_point_attempt": 1.0,
            },
            {
                "game_id": G1,
                "play_id": 3.0,
                "rush_attempt": 1.0,
                "rusher_player_id": "R1",
                "yards_gained": 6.0,
            },
        ]
    )
    pools = yards_pools(pbp, _ff([(G1, "R1", "RB")]), pricer_window("S2022"))
    assert pools.per_carry == {"RB": (6.0,)} and pools.per_reception == {}


def test_plays_with_no_ff_row_for_that_game_are_dropped_and_counted() -> None:
    pbp = _pbp(
        [
            {
                "game_id": G1,
                "play_id": 1.0,
                "rush_attempt": 1.0,
                "rusher_player_id": "R1",
                "yards_gained": 3.0,
            },
            {
                "game_id": G2,
                "play_id": 1.0,
                "rush_attempt": 1.0,
                "rusher_player_id": "R1",
                "yards_gained": 4.0,
            },
            {
                "game_id": G2,
                "play_id": 2.0,
                "complete_pass": 1.0,
                "receiver_player_id": "W9",
                "yards_gained": 11.0,
            },
        ]
    )
    pools = yards_pools(pbp, _ff([(G1, "R1", "RB")]), pricer_window("S2022"))
    assert pools.per_carry == {"RB": (3.0,)}
    assert pools.dropped_carries == 1 and pools.dropped_receptions == 1


def test_null_player_and_out_of_window_plays_never_enter() -> None:
    later = "2022_01_TMA_TMB"
    pbp = _pbp(
        [
            {
                "game_id": G1,
                "play_id": 1.0,
                "rush_attempt": 1.0,
                "rusher_player_id": None,
                "yards_gained": 3.0,
            },
            {
                "game_id": later,
                "play_id": 1.0,
                "rush_attempt": 1.0,
                "rusher_player_id": "R1",
                "yards_gained": 40.0,
            },
            {
                "game_id": G1,
                "play_id": 2.0,
                "rush_attempt": 1.0,
                "rusher_player_id": "R1",
                "yards_gained": 5.0,
            },
        ]
    )
    ff = _ff([(G1, "R1", "RB"), (later, "R1", "RB")])
    pools = yards_pools(pbp, ff, pricer_window("S2022"))
    assert pools.per_carry == {"RB": (5.0,)}
    assert pools.dropped_carries == 0
    assert pools.seasons == (2021,)


def test_a_player_with_two_groups_in_one_game_stops() -> None:
    pbp = _pbp(
        [
            {
                "game_id": G1,
                "play_id": 1.0,
                "rush_attempt": 1.0,
                "rusher_player_id": "R1",
                "yards_gained": 3.0,
            }
        ]
    )
    with pytest.raises(ValueError, match="PRV-06"):
        yards_pools(pbp, _ff([(G1, "R1", "RB"), (G1, "R1", "WR")]), pricer_window("S2022"))


def test_identical_duplicate_ff_rows_do_not_double_plays() -> None:
    pbp = _pbp(
        [
            {
                "game_id": G1,
                "play_id": 1.0,
                "rush_attempt": 1.0,
                "rusher_player_id": "R1",
                "yards_gained": 3.0,
            }
        ]
    )
    pools = yards_pools(pbp, _ff([(G1, "R1", "RB"), (G1, "R1", "RB")]), pricer_window("S2022"))
    assert pools.per_carry == {"RB": (3.0,)}


def test_pools_do_not_depend_on_row_order() -> None:
    rows = [
        {
            "game_id": g,
            "play_id": float(p),
            "rush_attempt": 1.0,
            "rusher_player_id": "R1",
            "yards_gained": float(y),
        }
        for g, p, y in ((G2, 3, 1), (G1, 9, 2), (G1, 2, 3), (G2, 1, 4))
    ]
    ff = _ff([(G1, "R1", "RB"), (G2, "R1", "RB")])
    a = yards_pools(_pbp(rows), ff, pricer_window("S2022"))
    b = yards_pools(_pbp(rows[::-1]), ff.reverse(), pricer_window("S2022"))
    assert a == b
    assert a.per_carry == {"RB": (3.0, 2.0, 4.0, 1.0)}


# ---- point-in-time mu for one game ----

FIT = Prv03Fit(
    window="test",
    usage_half_life=6.0,
    k={"receptions": 40.0, "receiving_yards": 40.0, "rushing_yards": 40.0},
    efficiency_half_life=8.0,
)
MEANS = Centring(
    means={
        (g, s): 0.0
        for g in ("QB", "RB", "WR", "TE", "Other")
        for s in ("receptions", "receiving_yards", "rushing_yards")
    },
    label="test",
)


def _games(teams: tuple[str, ...], weeks: tuple[int, ...]) -> pl.DataFrame:
    rows = [
        {"team": t, "game_id": f"2021_{w:02d}_TMA_TMB", "week": w, "g": float(i)}
        for t in teams
        for i, w in enumerate(sorted(weeks, reverse=True))
    ]
    return pl.DataFrame(
        rows, schema={"team": pl.Utf8, "game_id": pl.Utf8, "week": pl.Int64, "g": pl.Float64}
    )


def test_game_mu_prices_every_player_with_a_stint_row_on_either_team() -> None:
    weeks = (1, 2, 3)
    rows = []
    for w in weeks:
        g = f"2021_{w:02d}_TMA_TMB"
        rows += [(g, "A1", "WR", "TMA"), (g, "B1", "RB", "TMB")]
    rows.append(("2021_03_TMA_TMB", "A2", "TE", "TMA"))  # one game only
    rows.append(("2020_17_TMA_TMC", "C1", "WR", "TMA"))  # earlier season: not a candidate
    schema = {
        c: pl.Utf8 if c in ("game_id", "player_id", "posteam", "position") else pl.Float64
        for c in FF_OPPORTUNITY_COLUMNS
    }
    ff = pl.DataFrame(
        [
            {c: 0.0 for c in FF_OPPORTUNITY_COLUMNS}
            | {
                "game_id": g,
                "player_id": p,
                "position": pos,
                "posteam": t,
                "rec_attempt": 2.0,
                "receptions": 1.0,
                "receptions_exp": 1.0,
            }
            for g, p, pos, t in rows
        ],
        schema=schema,
    )
    out = game_mu(
        ff,
        _games(("TMA", "TMB"), weeks),
        target_game_id="2021_04_TMA_TMB",
        teams=("TMA", "TMB"),
        fit=FIT,
        centring_means=MEANS,
        as_of=dt.datetime(2021, 10, 1, tzinfo=dt.UTC),
    )
    assert out.height == 3 * 3  # A1, A2, B1 x 3 stats
    assert sorted(out["gsis_id"].unique().to_list()) == ["A1", "A2", "B1"]
    a1 = out.filter((pl.col("gsis_id") == "A1") & (pl.col("stat") == "receptions")).row(
        0, named=True
    )
    assert a1["team"] == "TMA" and a1["reason"] is None and a1["mu"] == pytest.approx(1.0)
    a2 = out.filter(pl.col("gsis_id") == "A2")["reason"].unique().to_list()
    assert a2 == [PricerUnpriced.TOO_FEW_STINT_GAMES.value]
    assert set(out.columns) >= {
        "game_id",
        "as_of",
        "team",
        "gsis_id",
        "stat",
        "mu",
        "e",
        "m",
        "g",
        "carries_mean",
        "n_games",
        "group",
        "reason",
        "centring_label",
        "fit_window",
    }
    assert out["fit_window"].unique().to_list() == ["test"]
    # deterministic row order
    assert out.equals(out.sort("team", "gsis_id", "stat"))
