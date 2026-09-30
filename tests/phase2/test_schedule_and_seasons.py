"""BT-01: the target game's schedule row, and season-level visibility rules, on real slices."""

import datetime as dt

import polars as pl

from ge.store.known_at import (
    CLOSING_LINES,
    OBSERVED_AS_FORECAST_PROXY,
    TARGET_NEVER,
    mask_target_schedule,
    ngs_visible,
    prior_seasons_only,
    with_kickoff,
)
from tests.phase2.conftest import load_parquet_fixture


def _played() -> dict:
    s = with_kickoff(load_parquet_fixture("schedules_2023_2026"))
    row = s.filter(pl.col("result").is_not_null() & pl.col("spread_line").is_not_null()).row(
        0, named=True
    )
    return row


def _mask(as_of: dt.datetime, flag: bool = False) -> tuple[pl.DataFrame, list[str]]:
    g = _played()
    return mask_target_schedule(pl.DataFrame([g]), as_of, closing_line_backtest=flag)


def test_scores_result_and_starting_qbs_never_visible() -> None:
    k = _played()["kickoff_utc"]
    for as_of, flag in ((k - dt.timedelta(days=1), False), (k + dt.timedelta(days=30), True)):
        df, _ = _mask(as_of, flag)
        assert not set(TARGET_NEVER) & set(df.columns)
    assert {"away_score", "home_score", "result", "total", "overtime"} <= set(TARGET_NEVER)


def test_closing_lines_hidden_before_kickoff() -> None:
    k = _played()["kickoff_utc"]
    df, labels = _mask(k - dt.timedelta(seconds=1))
    assert not set(CLOSING_LINES) & set(df.columns)
    assert any("closing lines hidden" in lb for lb in labels)
    assert {"spread_line", "total_line", "away_moneyline", "home_moneyline"} <= set(CLOSING_LINES)


def test_closing_lines_shown_at_kickoff_or_with_flag() -> None:
    g = _played()
    k = g["kickoff_utc"]
    for as_of, flag, why in (
        (k, False, "as_of at or after kickoff"),
        (k - dt.timedelta(days=1), True, "closing_line_backtest"),
    ):
        df, labels = _mask(as_of, flag)
        assert set(CLOSING_LINES) <= set(df.columns)
        assert df["spread_line"][0] == g["spread_line"]
        assert any(why in lb for lb in labels)


def test_temp_and_wind_labelled_observed() -> None:
    k = _played()["kickoff_utc"]
    df, labels = _mask(k - dt.timedelta(days=1))
    assert {"temp", "wind"} <= set(df.columns)
    assert any(OBSERVED_AS_FORECAST_PROXY in lb for lb in labels)


def test_ngs_season_totals_and_postseason_only_from_prior_seasons() -> None:
    ngs = load_parquet_fixture("nextgen_passing_2024_one_team")
    assert (ngs["week"] == 0).any() and (ngs["season_type"] == "POST").any()
    team = ngs["team_abbr"][0]
    finished = pl.DataFrame(
        {"season": [2024] * 22, "week": list(range(1, 23)), "team": [team] * 22}
    )
    same = ngs_visible(ngs, target_season=2024, finished_team_weeks=finished)
    assert not (same["week"] == 0).any()
    assert not (same["season_type"] == "POST").any()
    assert same.height == ngs.filter((pl.col("week") > 0) & (pl.col("season_type") == "REG")).height
    none_done = ngs_visible(ngs, target_season=2024, finished_team_weeks=finished.head(0))
    assert none_done.is_empty()
    later = ngs_visible(ngs, target_season=2025, finished_team_weeks=finished.head(0))
    assert later.height == ngs.height


def test_prior_seasons_only() -> None:
    ngs = load_parquet_fixture("nextgen_passing_2024_one_team")
    assert prior_seasons_only(ngs, 2024).is_empty()
    assert prior_seasons_only(ngs, 2025).height == ngs.height
