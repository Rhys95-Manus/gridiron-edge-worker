"""PRJ-01a Phase 4 report pieces, on hand-made frames, synthetic plays and the fixture store.

- The spread_line / total_line sign check must pass before any comparison, and abort when a
  line's sign is flipped.
- Differences, mean absolute and mean signed (bias) per season.
- Totals error against team pace (descriptive): equal-count bins and the OLS slope.
- The run-penalty sensitivity check's next-week prediction errors (report only).
- write_report on the fixture writes the Markdown and per-game CSV with the required sections."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from ge.config import ATTRIBUTION
from ge.metrics.coaching import CoachingRegistry
from ge.models.ratings import fit_ratings
from ge.models.ratings_report import (
    LineSignError,
    ReportSettings,
    check_line_signs,
    compare_to_lines,
    next_week_errors,
    pace_breakdown,
    summarise,
    write_report,
)
from tests.phase3.conftest import STORE
from tests.phase4 import synth


def _schedules(flip_spread: bool = False, flip_total: bool = False) -> pl.DataFrame:
    g = synth.rng("report/lines")
    n = 40
    margin = g.normal(0, 13, n)
    total = g.normal(45, 10, n)
    spread_line = 0.5 * margin + g.normal(0, 4, n)
    total_line = 0.5 * total + 22 + g.normal(0, 3, n)
    home = np.round(total / 2 + margin / 2)
    away = np.round(total / 2 - margin / 2)
    return pl.DataFrame(
        {
            "season": [3001] * (n // 2) + [3002] * (n // 2),
            "game_id": [f"g{i}" for i in range(n)],
            "home_score": home,
            "away_score": away,
            "spread_line": -spread_line if flip_spread else spread_line,
            "total_line": -total_line if flip_total else total_line,
        }
    )


def test_sign_check_passes_and_reports_correlations() -> None:
    got = check_line_signs(_schedules())
    assert got["season"].to_list() == [3001, 3002]
    assert (got["corr_spread"] > 0).all() and (got["corr_total"] > 0).all()


@pytest.mark.parametrize(("flip_spread", "flip_total"), [(True, False), (False, True)])
def test_sign_check_aborts_on_a_flipped_line(flip_spread: bool, flip_total: bool) -> None:
    with pytest.raises(LineSignError):
        check_line_signs(_schedules(flip_spread, flip_total))


def test_differences_and_summary() -> None:
    rated = pl.DataFrame(
        {
            "season": [3001, 3001, 3002],
            "week": [1, 2, 1],
            "game_id": ["a", "b", "c"],
            "game_type": ["REG", "REG", "REG"],
            "spread": [3.0, -1.0, 7.0],
            "total": [44.0, 50.0, 40.0],
        }
    )
    sched = pl.DataFrame(
        {
            "game_id": ["a", "b", "c"],
            "spread_line": [2.5, 1.0, 3.0],
            "total_line": [45.0, 47.5, 41.0],
            "home_score": [24, 17, 30],
            "away_score": [20, 21, 10],
        }
    )
    cmp = compare_to_lines(rated, sched).sort("game_id")
    assert cmp["spread_diff"].to_list() == [0.5, -2.0, 4.0]
    assert cmp["total_diff"].to_list() == [-1.0, 2.5, -1.0]
    assert cmp["spread_vs_actual"].to_list() == [3.0 - 4, -1.0 - (-4), 7.0 - 20]
    assert cmp["total_vs_actual"].to_list() == [44.0 - 44, 50.0 - 38, 40.0 - 40]
    s = summarise(cmp).filter(pl.col("week").is_null()).sort("season")
    r = s.row(0, named=True)
    assert r["n"] == 2
    assert r["spread_mad"] == pytest.approx(1.25) and r["spread_bias"] == pytest.approx(-0.75)
    assert r["total_mad"] == pytest.approx(1.75) and r["total_bias"] == pytest.approx(0.75)


def test_pace_breakdown_bins_and_slope() -> None:
    g = synth.rng("report/pace")
    n = 100
    pace = g.uniform(110, 140, n)
    cmp = pl.DataFrame(
        {
            "season": [3001] * n,
            "pace_plays": pace,
            "pace_seconds": g.uniform(25, 31, n),
            "total_diff": 0.5 * (pace - 125.0),
            "total_vs_actual": 0.5 * (pace - 125.0),
            "spread_diff": np.zeros(n),
        }
    )
    bins, slopes = pace_breakdown(cmp, 5)
    assert bins.height == 5 and bins["n"].to_list() == [20] * 5
    assert bins["total_diff_mean"].is_sorted()
    r = slopes.filter(pl.col("season") == 3001).row(0, named=True)
    assert r["total_slope"] == pytest.approx(0.5, abs=1e-9)
    assert r["total_slope_se"] == pytest.approx(0.0, abs=1e-9)
    assert r["spread_slope"] == pytest.approx(0.0, abs=1e-9)


def test_next_week_errors_match_manual_refits() -> None:
    small = synth.Settings(teams=8, seasons=1, weeks=4, plays_per_offense=40)
    d = synth.make("report/sensitivity", small)
    season = small.first_season
    plays = synth.with_offset(d.plays.filter(pl.col("season") == season), small.beta)
    got = next_week_errors(plays, d.teams, penalty=30.0, h=3.0, scales=(0.5, 1.0, 2.0))
    assert sorted(set(got["scale"].to_list())) == [0.5, 1.0, 2.0]
    for scale in (0.5, 1.0, 2.0):
        sq: dict[str, list[float]] = {"pass": [], "run": []}
        for week in range(2, small.weeks + 1):
            train = synth.with_games_ago(plays.filter(pl.col("week") < week))
            t = fit_ratings(
                train, d.teams, penalty=30.0, h=3.0, prior=None, run_penalty_scale=scale
            )
            for r in plays.filter(pl.col("week") == week).to_dicts():
                kind = "pass" if r["is_pass"] else "run"
                pred = (
                    (t.int_pass if kind == "pass" else t.int_run)
                    + t.values[(r["posteam"], f"off_{kind}")]
                    + t.values[(r["defteam"], f"def_{kind}")]
                    + r["offset"]
                )
                sq[kind].append((r["epa"] - pred) ** 2)
        for kind in ("pass", "run"):
            row = got.filter((pl.col("scale") == scale) & (pl.col("side") == kind)).row(
                0, named=True
            )
            assert row["n"] == len(sq[kind])
            assert row["mse"] == pytest.approx(math.fsum(sq[kind]) / len(sq[kind]), rel=1e-12)


@pytest.mark.usefixtures("fit_env")
def test_write_report_on_fixture(
    tmp_path: Path, ratings_root: Path, registry: CoachingRegistry
) -> None:
    settings = ReportSettings(sensitivity_seasons=(2024,), scales=(0.5, 1.0, 2.0), pace_bins=2)
    path = write_report(
        [2024],
        settings,
        weeks=[7, 8],
        root=STORE,
        ratings_root=ratings_root,
        registry=registry,
        out_dir=tmp_path,
    )
    assert path == tmp_path / "ratings_walkforward.md"
    md = path.read_text(encoding="utf-8")
    csv = pl.read_csv(tmp_path / "ratings_walkforward.csv")
    assert b"\r\n" not in path.read_bytes()
    for needle in (
        ATTRIBUTION,
        "spread_line",
        "home team favoured",
        "approximate",
        "COA-07",
        "points per drive",
        "pace",
        "sensitivity",
        "0.5x",
        "2x",
        "S2024",
        "overtime",
    ):
        assert needle in md, needle
    sched = pl.read_parquet(
        sorted((STORE / "schedules" / "season=2024").glob("*/part.parquet"))[-1]
    )
    want = sched.filter(pl.col("week").is_in([7, 8]))["game_id"].sort().to_list()
    assert csv["game_id"].sort().to_list() == want
    rated = csv.filter(pl.col("skip_reason").is_null())
    assert rated.height > 0
    for col in (
        "spread",
        "spread_se",
        "total",
        "total_se",
        "spread_line",
        "total_line",
        "pace_plays",
    ):
        assert rated[col].null_count() == 0, col
