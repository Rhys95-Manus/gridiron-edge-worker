"""PRJ-02 overtime (rulings 2026-10-23, B7 and the overtime rulings): entries live in
config/overtime.yaml, one per season the simulator runs (2021-2024 and 2026) and game type.
Each cites the official NFL rulebook page: 2021-2024 through an archived copy (archive URL,
original URL, capture date inside the season); 2026 from the live official page, rendered in a
browser, with its retrieval date. Each carries one verbatim quote under 15 words and the format
in our own words. A season with no entry raises; no other source is substituted."""

from __future__ import annotations

import datetime as dt

import pytest

from ge.models.sim.overtime import OvertimeRuleMissing, load_overtime, overtime_rule

ARCHIVED = (2021, 2022, 2023, 2024)
SIM_SEASONS = (*ARCHIVED, 2026)


def _in_season(d: dt.date, season: int) -> bool:
    return dt.date(season, 9, 1) <= d <= dt.date(season + 1, 2, 28)


@pytest.mark.parametrize("season", [2016, 2020, 2025, 2027])
def test_season_without_entry_raises(season: int) -> None:
    with pytest.raises(OvertimeRuleMissing, match="PRJ-02"):
        overtime_rule(season, postseason=False)


@pytest.mark.parametrize("season", SIM_SEASONS)
@pytest.mark.parametrize("postseason", [False, True])
def test_entry_cites_the_official_rulebook(season: int, postseason: bool) -> None:
    rule = overtime_rule(season, postseason=postseason)
    assert rule.spec_id == "PRJ-02"
    assert rule.original_url.startswith("https://operations.nfl.com/")
    assert 0 < len(rule.quote.split()) < 15, "one verbatim quote under 15 words"
    if season in ARCHIVED:
        assert rule.text_read_from == "archive"
        assert rule.archive_url is not None
        assert rule.archive_url.startswith("https://web.archive.org/web/")
        assert rule.archive_url.endswith(rule.original_url)
        assert _in_season(dt.date.fromisoformat(rule.capture_date), season)
    else:
        assert rule.text_read_from == "live"
        assert _in_season(dt.date.fromisoformat(rule.capture_date), season)


@pytest.mark.parametrize("season", SIM_SEASONS)
def test_format_is_complete(season: int) -> None:
    reg = overtime_rule(season, postseason=False)
    post = overtime_rule(season, postseason=True)
    assert reg.max_periods == 1 and reg.ties_allowed
    assert post.max_periods is None and not post.ties_allowed
    assert reg.period_minutes > 0 and post.period_minutes > 0
    assert reg.timeouts_per_team > 0 and post.timeouts_per_team > 0


def test_every_entry_is_for_a_simulated_season() -> None:
    entries = load_overtime()
    assert {(e.season, e.postseason) for e in entries} == {
        (s, p) for s in SIM_SEASONS for p in (False, True)
    }
