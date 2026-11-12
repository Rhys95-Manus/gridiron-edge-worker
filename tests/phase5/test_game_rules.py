"""PRJ-02 game-rule constants (ruling E2, 2026-10-24): config/game_rules.yaml, built like
config/overtime.yaml. Each value cites the official NFL rulebook page for every season it covers
(archived captures inside 2021-2024, the live page for 2026) with a verbatim quote under 15
words; a value read for a season it does not cover raises."""

from __future__ import annotations

import datetime as dt

import pytest

from ge.models.sim.rules import GameRuleMissing, game_rule, load_game_rules

SIM_SEASONS = (2021, 2022, 2023, 2024, 2026)
EXPECTED_KEYS = {
    "touchdown_points",
    "field_goal_points",
    "safety_points",
    "try_kick_points",
    "try_run_pass_points",
    "line_to_gain_yards",
    "downs_per_series",
    "field_of_play_yards",
    "end_zone_yards",
    "periods",
    "period_minutes",
    "timeouts_per_half",
    "two_minute_warning_seconds",
}


def test_every_rule_the_simulator_needs_is_present() -> None:
    assert set(load_game_rules().rules) == EXPECTED_KEYS


def test_quotes_are_short_and_sources_are_in_season() -> None:
    f = load_game_rules()
    for key, r in f.rules.items():
        for q in r.quotes:
            assert 0 < len(q.split()) < 15, (key, q)
        assert set(r.seasons) <= set(f.sources), key
    for season, s in f.sources.items():
        assert s.original_url.startswith("https://operations.nfl.com/")
        d = dt.date.fromisoformat(s.capture_date)
        assert dt.date(season, 9, 1) <= d <= dt.date(season + 1, 2, 28), (season, d)
        if s.text_read_from == "archive":
            assert s.archive_url is not None and s.archive_url.endswith(s.original_url)


@pytest.mark.parametrize("season", SIM_SEASONS)
def test_scoring_values(season: int) -> None:
    assert game_rule("touchdown_points", season) == 6
    assert game_rule("field_goal_points", season) == 3
    assert game_rule("safety_points", season) == 2
    assert game_rule("try_kick_points", season) == 1
    assert game_rule("try_run_pass_points", season) == 2


def test_field_of_play_is_not_sourced_for_2026() -> None:
    """The 2026 page does not carry the field-length wording; no other source is substituted."""
    assert game_rule("field_of_play_yards", 2024) == 100
    with pytest.raises(GameRuleMissing, match="PRJ-02"):
        game_rule("field_of_play_yards", 2026)


@pytest.mark.parametrize("season", [2020, 2025])
def test_unsourced_season_raises(season: int) -> None:
    with pytest.raises(GameRuleMissing, match="PRJ-02"):
        game_rule("touchdown_points", season)
