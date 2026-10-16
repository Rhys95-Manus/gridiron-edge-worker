"""Phase 4b acceptance (BUILD_PLAN Phase 4b), on the committed walk-forward report's per-game
rows (reports/phase4/ratings_walkforward.csv, from `ge ratings-report --seasons 2021-2024`).
Run locally, not in CI. Every season 2021-2024:

1. "the 95% interval for the calibrated spread slope against actual results covers 1";
2. "the slope against closing lines is within 0.85-1.15";
3. "spread bias is within +/-0.5 points" (regular-season games only; postseason is reported
   separately and doesn't count; ruling 2026-10-14);
4. "week-1 games are rated except where no depth chart exists".

The thresholds are the Build Plan's; they live here, not in params.yaml (ruling 2026-10-14).
If any check fails, Phase 4b stops and reports; nothing is tuned on 2021-2024 results."""

from __future__ import annotations

import polars as pl
import pytest

from ge.models.ratings_report import REPORT_ROOT, calibration

pytestmark = pytest.mark.realdata

SEASONS = (2021, 2022, 2023, 2024)
Z95 = 1.96
CLOSING_SLOPE = (0.85, 1.15)
BIAS_POINTS = 0.5


@pytest.fixture(scope="module")
def games() -> pl.DataFrame:
    return pl.read_csv(REPORT_ROOT / "ratings_walkforward.csv", infer_schema_length=None)


@pytest.fixture(scope="module")
def calib(games: pl.DataFrame) -> pl.DataFrame:
    return calibration(games.filter(pl.col("skip_reason").is_null()))


def test_report_covers_every_season(games: pl.DataFrame) -> None:
    assert sorted(set(games["season"].to_list())) == list(SEASONS)


@pytest.mark.parametrize("season", SEASONS)
def test_calibrated_slope_against_actual_covers_one(calib: pl.DataFrame, season: int) -> None:
    r = calib.filter(
        (pl.col("season") == season)
        & (pl.col("model") == "spread")
        & (pl.col("target") == "actual")
    ).row(0, named=True)
    lo, hi = r["slope"] - Z95 * r["slope_se"], r["slope"] + Z95 * r["slope_se"]
    assert lo <= 1.0 <= hi, (season, r["slope"], r["slope_se"])


@pytest.mark.parametrize("season", SEASONS)
def test_calibrated_slope_against_closing_line(calib: pl.DataFrame, season: int) -> None:
    r = calib.filter(
        (pl.col("season") == season)
        & (pl.col("model") == "spread")
        & (pl.col("target") == "closing_line")
    ).row(0, named=True)
    assert CLOSING_SLOPE[0] <= r["slope"] <= CLOSING_SLOPE[1], (season, r["slope"])


@pytest.mark.parametrize("season", SEASONS)
def test_regular_season_spread_bias(games: pl.DataFrame, season: int) -> None:
    d = games.filter(
        (pl.col("season") == season)
        & (pl.col("game_type") == "REG")
        & pl.col("skip_reason").is_null()
    ).drop_nulls(["spread_diff"])
    bias = float(d["spread_diff"].mean())  # type: ignore[arg-type]
    assert abs(bias) <= BIAS_POINTS, (season, bias, d.height)


@pytest.mark.parametrize("season", SEASONS)
def test_week1_rated_except_without_a_depth_chart(games: pl.DataFrame, season: int) -> None:
    w1 = games.filter((pl.col("season") == season) & (pl.col("week") == 1))
    unrated = w1.filter(pl.col("skip_reason").is_not_null())
    other = unrated.filter(~pl.col("skip_reason").str.contains("depth chart"))
    assert other.is_empty(), other.select("game_id", "skip_reason").rows()
