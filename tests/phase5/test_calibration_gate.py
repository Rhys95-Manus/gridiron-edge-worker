"""PRJ-02 calibration gate, 2021-2024 (plan plans/phase5-calibration-gate.md; rulings 2026-11-21,
Rhys "Accept recommendations"). Gated, every season (G-Q1 (i)): the PRJ-02 acceptance test's
league averages, points per team-game, plays per team-game, pass rate and yards per pass attempt,
within the params.yaml tolerances, on the games the run simulated (G-Q3; skips are reported).
Definitions (ruling E14, 2026-10-24): plays = OFF-11 qualifying plays (pass or rush, scrimmage,
not G7 garbage time); pass rate = qualifying pass plays (sacks and scrambles included) /
qualifying plays; yards per pass attempt = passing yards on attempts (sacks excluded) /
attempts; points = final score including overtime. Computed the same way for the simulation
and for nflverse. Reported, not gated: margin SD, margin/total calibration, the pace check,
xpass/cp agreement, ERA5 agreement, timing. Synthetic placeholder data only, except the realdata
tests at the end."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from ge.config import load_params
from ge.models.sim import gate
from ge.store.holdout import HoldoutReadError

GATE_TAG = "phase5-gate1"  # ruling G-Q6, 2026-11-21
SEASONS = (2021, 2022, 2023, 2024)


# ---------------------------------------------------------------- tolerances


def test_tolerances_come_from_params() -> None:
    p = load_params().projection
    want = {
        "points_per_team_game": p.prj_02_tol_points_per_team_game,
        "plays_per_team_game": p.prj_02_tol_plays_per_team_game,
        "pass_rate": p.prj_02_tol_pass_rate,
        "yards_per_pass_attempt": p.prj_02_tol_yards_per_pass_attempt,
    }
    got = gate.tolerances()
    assert tuple(got) == gate.GATE_METRICS == tuple(want)
    for k, e in want.items():
        assert e.spec_id == "PRJ-02"
        assert got[k] == float(e.value)


# ---------------------------------------------------------------- simulation side


def _sim_rows() -> pl.DataFrame:
    rows = [
        # game, skip, pts h/a, plays_g7 h/a, pass_plays_g7 h/a, pass_yds h/a, att h/a, plays h/a
        ("G1", None, 24.0, 17.0, 60.0, 64.0, 36.0, 40.0, 250.0, 210.0, 34.0, 38.0, 63.0, 66.0),
        ("G2", None, 20.0, 27.0, 58.0, 62.0, 30.0, 35.0, 190.0, 260.0, 28.0, 33.0, 61.0, 64.0),
        ("G3", "PRJ-02 skipped (test)", *([None] * 12)),
    ]
    cols = ["game_id", "skip_reason", "home_points", "away_points", "home_plays_g7",
            "away_plays_g7", "home_pass_plays_g7", "away_pass_plays_g7", "home_pass_yds",
            "away_pass_yds", "home_pass_att", "away_pass_att", "home_plays",
            "away_plays"]  # fmt: skip
    return pl.DataFrame(rows, schema=cols, orient="row")


def test_sim_averages_hand_computed() -> None:
    ok = _sim_rows().filter(pl.col("skip_reason").is_null())
    got = gate.sim_averages(ok)
    assert got["points_per_team_game"] == pytest.approx((24 + 17 + 20 + 27) / 4)
    assert got["plays_per_team_game"] == pytest.approx((60 + 64 + 58 + 62) / 4)
    assert got["pass_rate"] == pytest.approx((36 + 40 + 30 + 35) / (60 + 64 + 58 + 62))
    assert got["yards_per_pass_attempt"] == pytest.approx(
        (250 + 210 + 190 + 260) / (34 + 38 + 28 + 33)
    )
    # ruling D1: reported alongside, not gated
    assert gate.REPORTED_ALONGSIDE == ("plays_per_team_game_no_g7",)
    assert got["plays_per_team_game_no_g7"] == pytest.approx((63 + 66 + 61 + 64) / 4)


def test_sim_averages_refuse_skipped_rows() -> None:
    with pytest.raises(ValueError, match="PRJ-02"):
        gate.sim_averages(_sim_rows())


# ---------------------------------------------------------------- actual side


def _pbp() -> pl.DataFrame:
    rows = [
        # game, posteam, play_type, pass, rush, kneel, spike, 2pt, qtr, wp, att, sack, cmp, yds
        ("G1", "H", "pass", 1, 0, 0, 0, 0, 1, 0.5, 1, 0, 1, 12.0),  # completion
        ("G1", "H", "pass", 1, 0, 0, 0, 0, 1, 0.5, 1, 0, 0, 0.0),  # incompletion
        ("G1", "H", "pass", 1, 0, 0, 0, 0, 2, 0.5, 0, 1, 0, -7.0),  # sack: pass play, no attempt
        ("G1", "H", "run", 0, 1, 0, 0, 0, 2, 0.5, 0, 0, 0, 4.0),  # designed run
        ("G1", "A", "run", 1, 0, 0, 0, 0, 3, 0.5, 0, 0, 0, 9.0),  # scramble: pass play
        ("G1", "A", "pass", 1, 0, 0, 0, 0, 4, 0.99, 1, 0, 1, 20.0),  # G7: attempt counts, play no
        ("G1", "A", "qb_kneel", 0, 1, 1, 0, 0, 4, 0.5, 0, 0, 0, -1.0),  # kneel: out
        ("G1", "A", "pass", 1, 0, 0, 0, 1, 3, 0.5, 1, 0, 1, 2.0),  # two-point try: out
        ("G1", "A", "no_play", 1, 0, 0, 0, 0, 3, 0.5, 0, 0, 0, 0.0),  # no-play penalty: out
        ("G1", None, "kickoff", 0, 0, 0, 0, 0, 1, 0.5, 0, 0, 0, 0.0),  # no possession
    ]
    cols = ["game_id", "posteam", "play_type", "pass", "rush", "qb_kneel", "qb_spike",
            "two_point_attempt", "qtr", "wp", "pass_attempt", "sack", "complete_pass",
            "yards_gained"]  # fmt: skip
    return pl.DataFrame(rows, schema=cols, orient="row")


def _sched() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["G1"],
            "home_team": ["H"],
            "away_team": ["A"],
            "home_score": [23],
            "away_score": [20],
        }
    )


def test_actual_averages_hand_computed() -> None:
    got = gate.actual_averages(_pbp(), _sched())
    assert got["points_per_team_game"] == pytest.approx(43 / 2)
    # qualifying: completion, incompletion, sack, run, scramble (G7, kneel, 2pt, no-play out)
    assert got["plays_per_team_game"] == pytest.approx(5 / 2)
    assert got["pass_rate"] == pytest.approx(4 / 5)
    assert got["plays_per_team_game_no_g7"] == pytest.approx(6 / 2)  # D1: the G7 pass back in
    # attempts: completion, incompletion, the G7 completion (no sack, no try) = 3; yards 12 + 20
    assert got["yards_per_pass_attempt"] == pytest.approx(32 / 3)


def test_check_marks_pass_and_fail_at_the_tolerance() -> None:
    tol = gate.tolerances()
    sim = {k: 10.0 for k in gate.GATE_METRICS}
    act = dict(sim)
    act["points_per_team_game"] = 10.0 + tol["points_per_team_game"]  # at the edge: passes
    act["pass_rate"] = 10.0 - 2 * tol["pass_rate"]  # beyond: fails
    rows = {r["metric"]: r for r in gate.check(sim, act).iter_rows(named=True)}
    assert tuple(rows) == gate.GATE_METRICS
    assert rows["points_per_team_game"]["passed"] is True
    assert rows["pass_rate"]["passed"] is False
    assert rows["plays_per_team_game"]["passed"] is True
    assert rows["pass_rate"]["diff"] == pytest.approx(2 * tol["pass_rate"])
    assert rows["pass_rate"]["tolerance"] == tol["pass_rate"]


# ---------------------------------------------------------------- games and holdout


def test_simulated_games_rejects_missing_and_extra_games() -> None:
    sim = _sim_rows()
    ok, skipped = gate.simulated_games(sim, ["G1", "G2", "G3"])
    assert ok["game_id"].to_list() == ["G1", "G2"] and skipped["game_id"].to_list() == ["G3"]
    with pytest.raises(ValueError, match=r"PRJ-02.*missing"):
        gate.simulated_games(sim, ["G1", "G2", "G3", "G4"])
    with pytest.raises(ValueError, match=r"PRJ-02.*not in the season"):
        gate.simulated_games(sim, ["G1", "G2"])


def test_gate_refuses_the_holdout_before_any_read(tmp_path) -> None:  # type: ignore[no-untyped-def]
    holdout = int(load_params().backtest.bt_01_holdout_season.value)
    with pytest.raises(HoldoutReadError):
        gate.season_gate("no-such-tag", holdout, runs_root=tmp_path, data_root=tmp_path)
    with pytest.raises(HoldoutReadError):  # 2024 comes first and would fail to read
        gate.actual_margin_sd([2024, holdout], data_root=tmp_path)


# ---------------------------------------------------------------- reported quantities


def test_margin_sd_seasons_are_the_bt01_range() -> None:
    b = load_params().backtest
    assert gate.margin_sd_seasons() == (
        b.bt_01_first_training_season.value,
        b.bt_01_last_test_season.value,
    )
    lo, hi = gate.margin_sd_seasons()
    assert b.bt_01_holdout_season.value not in range(lo, hi + 1)


def test_pooled_margin_sd_equals_the_sd_of_every_run() -> None:
    rng = np.random.default_rng(7)
    a, b = rng.normal(3.0, 13.0, 500), rng.normal(-4.0, 11.0, 300)
    sim = pl.DataFrame(
        {
            "margin_mean": [a.mean(), b.mean()],
            "margin_sd": [a.std(), b.std()],
            "n_runs": [a.size, b.size],
        }
    )
    assert gate.pooled_margin_sd(sim) == pytest.approx(np.concatenate([a, b]).std())


def test_compared_frame_feeds_the_phase4_calibration() -> None:
    """Sim mean margin / total in the Phase 4 model columns; with actual = sim exactly the
    margin slope is 1 and the intercept 0."""
    from ge.models.ratings_report import calibration

    ok = pl.DataFrame(
        {
            "game_id": ["G1", "G2", "G3"],
            "season": [2024] * 3,
            "margin_mean": [3.0, -2.0, 7.0],
            "total_mean": [44.0, 40.0, 51.0],
        }
    )
    sched = pl.DataFrame(
        {
            "game_id": ["G1", "G2", "G3"],
            "game_type": ["REG"] * 3,
            "location": ["Home"] * 3,
            "spread_line": [2.5, -1.0, 6.5],
            "total_line": [44.5, 41.0, 50.0],
            "home_score": [23, 20, 30],
            "away_score": [20, 22, 23],
        }
    )
    comp = gate.compared(ok, sched, pace=None)
    assert comp["spread"].to_list() == [3.0, -2.0, 7.0]
    assert comp["total"].to_list() == [44.0, 40.0, 51.0]
    exact = comp.with_columns(
        (pl.col("spread") * 0 + pl.col("home_score") - pl.col("away_score")).alias("spread")
    )
    row = calibration(exact).filter((pl.col("model") == "spread") & (pl.col("target") == "actual"))
    assert row["slope"].item() == pytest.approx(1.0) and row["intercept"].item() == pytest.approx(0)


# ---------------------------------------------------------------- realdata: the gate (C1-C4)


@pytest.mark.realdata
@pytest.mark.parametrize("season", SEASONS)
def test_gate_league_averages(season: int) -> None:
    """G-Q1 (i): every season's league averages within the PRJ-02 tolerances, on the gate run
    (tag phase5-gate1, one commit, all four seasons). Never loosened; a failing season is
    reported, not tuned (BUILD_PLAN Phase 5)."""
    try:
        res = gate.season_gate(GATE_TAG, season)
    except FileNotFoundError as exc:
        pytest.fail(f"realdata gate needs the gate run and the local store: {exc}")
    failed = res.checks.filter(~pl.col("passed"))
    assert failed.height == 0, failed.to_dicts()
