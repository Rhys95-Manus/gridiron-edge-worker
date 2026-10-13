"""PRJ-01a report diagnostics added 2026-10-12 (user request after the decision-log sync):

- calibration: per season, the closing line and the actual result each regressed on the
  model spread (and on the model total), slope and intercept with standard errors;
- the combined COA-07 home effect in points (league drives x c x (home offset - away
  offset), each game with its own window's constants) next to the closing-line home edge
  (mean spread_line) and the mean actual home margin, non-neutral games only;
- the c diagnostic: league plays per drive, and c refit with turnover plays (interception
  or lost fumble) left out of x."""

from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from ge.metrics.coaching import CoachingRegistry
from ge.models.ratings_report import ReportSettings, calibration, home_edge, write_report
from ge.models.ratings_window import c_diagnostic, fit_c, team_games
from ge.store.holdout import Window
from tests.phase3 import oracle as o
from tests.phase3.conftest import STORE, store_table
from tests.phase4 import synth


def _ols(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float, float]:
    """Slope, slope se, intercept, intercept se (independent closed form)."""
    n = len(x)
    X = np.column_stack([np.ones(n), x])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    cov = (r @ r) / (n - 2) * np.linalg.inv(X.T @ X)
    return float(b[1]), float(math.sqrt(cov[1, 1])), float(b[0]), float(math.sqrt(cov[0, 0]))


def test_calibration_regressions() -> None:
    g = synth.rng("diag/calibration")
    n = 60
    spread = g.normal(0, 6, n)
    total = g.normal(44, 4, n)
    cmp = pl.DataFrame(
        {
            "season": [3001] * n,
            "game_type": ["REG"] * n,
            "spread": spread,
            "total": total,
            "spread_line": 0.8 * spread + 1.0 + g.normal(0, 2, n),
            "total_line": 0.9 * total + 3.0 + g.normal(0, 2, n),
            "home_score": np.round(24 + spread / 2 + g.normal(0, 7, n)),
            "away_score": np.round(20 - spread / 2 + g.normal(0, 7, n)),
        }
    )
    got = calibration(cmp)
    margin = (cmp["home_score"] - cmp["away_score"]).to_numpy().astype(float)
    points = (cmp["home_score"] + cmp["away_score"]).to_numpy().astype(float)
    want = {
        ("spread", "closing_line"): _ols(spread, cmp["spread_line"].to_numpy()),
        ("spread", "actual"): _ols(spread, margin),
        ("total", "closing_line"): _ols(total, cmp["total_line"].to_numpy()),
        ("total", "actual"): _ols(total, points),
    }
    assert got.height == 4
    for r in got.iter_rows(named=True):
        slope, slope_se, icpt, icpt_se = want[(r["model"], r["target"])]
        assert r["season"] == 3001 and r["n"] == n
        assert r["slope"] == pytest.approx(slope, rel=1e-10)
        assert r["slope_se"] == pytest.approx(slope_se, rel=1e-8)
        assert r["intercept"] == pytest.approx(icpt, rel=1e-10, abs=1e-12)
        assert r["intercept_se"] == pytest.approx(icpt_se, rel=1e-8)


def test_home_edge_in_points() -> None:
    cmp = pl.DataFrame(
        {
            "season": [3001, 3001, 3001, 3001],
            "game_type": ["REG"] * 4,
            "location": ["Home", "Home", "Neutral", "Home"],
            "home_offset": [0.010, 0.020, 0.000, 0.005],
            "away_offset": [-0.010, 0.000, 0.000, -0.005],
            "c": [3.0, 3.0, 3.0, 3.2],
            "league_drives": [11.0, 11.0, 11.0, 11.5],
            "spread_line": [3.0, -2.0, 1.0, 6.5],
            "home_score": [24, 17, 20, 30],
            "away_score": [20, 21, 10, 13],
        }
    )
    got = home_edge(cmp).row(0, named=True)
    pts = [11.0 * 3.0 * 0.020, 11.0 * 3.0 * 0.020, 11.5 * 3.2 * 0.010]
    assert got["n"] == 3
    assert got["model_coa07_home_points"] == pytest.approx(sum(pts) / 3, rel=1e-12)
    assert got["closing_line_home_edge"] == pytest.approx((3.0 - 2.0 + 6.5) / 3, rel=1e-12)
    assert got["actual_home_margin"] == pytest.approx((4 - 4 + 17) / 3, rel=1e-12)


def test_team_games_can_leave_out_turnovers() -> None:
    pbp = store_table("pbp", 2023)
    sched = store_table("schedules", 2023)
    got = {
        (r["game_id"], r["team"]): r
        for r in team_games(pbp, sched, exclude_turnovers=True).to_dicts()
    }
    plays: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in pbp.to_dicts():
        if not o.qualifying(r) or r["epa"] is None:
            continue
        if r["interception"] == 1 or r["fumble_lost"] == 1:
            continue
        plays[(r["game_id"], r["posteam"])].append(float(r["epa"]))
    assert got
    for key, r in got.items():
        assert r["plays"] == len(plays[key])
        assert r["epa_sum"] == pytest.approx(math.fsum(plays[key]), abs=1e-9)


@pytest.mark.usefixtures("fit_env")
def test_report_has_the_diagnostic_sections(
    tmp_path: Path, ratings_root: Path, registry: CoachingRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The report shows the three diagnostics. The c diagnostic reads each window's training
    seasons; the fixture holds only 2023, so the test window is narrowed to it."""
    import ge.models.ratings_report as rr

    monkeypatch.setattr(rr, "diagnostic_window", lambda season: Window("S2024", 2024, (2023,)))
    settings = ReportSettings(sensitivity_seasons=(2024,), scales=(1.0,), pace_bins=2)
    path = write_report(
        [2024],
        settings,
        weeks=[8],
        root=STORE,
        ratings_root=ratings_root,
        registry=registry,
        out_dir=tmp_path,
    )
    md = path.read_text(encoding="utf-8")
    for needle in ("Calibration", "closing-line home edge", "plays per drive", "turnover"):
        assert needle in md, needle


@pytest.mark.usefixtures("fit_env")
def test_c_diagnostic_on_fixture() -> None:
    window = Window("S2024", 2024, (2023,))
    got = c_diagnostic(window, dt.datetime(2026, 10, 12, tzinfo=dt.UTC), root=STORE)
    pbp, sched = store_table("pbp", 2023), store_table("schedules", 2023)
    all_games = team_games(pbp, sched)
    base = fit_c(all_games)
    no_to = fit_c(team_games(pbp, sched, exclude_turnovers=True))
    assert got["plays_per_drive"] == pytest.approx(
        float(all_games["plays"].sum() / all_games["drives"].sum()), rel=1e-12
    )
    assert (got["c"], got["c_se"]) == (base.c, base.c_se)
    assert (got["c_no_turnovers"], got["c_no_turnovers_se"]) == (no_to.c, no_to.c_se)
    assert got["n_team_games"] == base.n_team_games
