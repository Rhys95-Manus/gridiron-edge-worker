"""DATA-08: rule-based include/exclude *proposals* for NFL series candidates. Proposals never
change a decision; only the user marks include."""

import functools
from pathlib import Path
from typing import Any

import pytest
import yaml

from ge.ingest.kalshi import (
    Candidate,
    approved_series,
    fee_schedule_nfl_tickers,
    nfl_candidates,
    propose,
    update_review_file,
    write_proposals,
)
from tests.phase1.conftest import FIXTURES, load_fixture


@functools.cache
def _series() -> Any:
    return load_fixture("kalshi_series_subset.json")["response"]["series"]


@functools.cache
def _teams() -> Any:
    return [t["team_name"] for t in load_fixture("nflverse_teams.json")["response"]]


@functools.cache
def _pdf() -> Any:
    return (FIXTURES / "kalshi_fee_schedule.pdf").read_bytes()


BY_TICKER = {s["ticker"]: s for s in _series()}


def _proposals() -> dict[str, tuple[str, list[str]]]:
    return propose(nfl_candidates(_series()), _teams(), fee_schedule_nfl_tickers(_pdf()))


def test_fee_schedule_nfl_tickers_come_from_the_pdf() -> None:
    tickers = fee_schedule_nfl_tickers(_pdf())
    assert "KXNFLGAME" in tickers
    assert all(t.startswith("KX") for t in tickers)
    assert not any("NCAA" in t for t in tickers), "college series must not count as NFL"


def test_every_candidate_gets_a_proposal_with_rules() -> None:
    props = _proposals()
    assert set(props) == {c.ticker for c in nfl_candidates(_series())}
    for ticker, (proposal, rules) in props.items():
        assert proposal in {"include", "exclude", "undecided"}, ticker
        assert rules, ticker


def test_college_and_other_leagues_are_excluded() -> None:
    props = _proposals()
    college = [t for t in props if "NCAAF" in t]
    assert college
    assert all(props[t][0] == "exclude" and "other_league" in props[t][1] for t in college)


OTHER_PRO_LEAGUES = ("NBA", "WNBA", "NHL", "MLB", "MLS")


def test_other_pro_league_candidates_in_real_series_are_excluded() -> None:
    """Kalshi sometimes tags other leagues' series Football (decision 2026-10-02)."""
    props = _proposals()
    hits = [t for t in props if any(code in t for code in OTHER_PRO_LEAGUES)]
    assert hits, "expected an other-league candidate in the series fixture"
    for t in hits:
        assert props[t][0] == "exclude" and "other_league" in props[t][1], (t, props[t])


@pytest.mark.parametrize("code", OTHER_PRO_LEAGUES)
def test_other_pro_league_in_ticker_or_title_is_excluded(code: str) -> None:
    # Placeholder tickers and titles, not real series: this checks the string rule only.
    by_ticker = Candidate(
        f"KXTEST{code}X", "Test series", "Sports", ("Football",), None, None, ("tag:Football",)
    )
    by_title = Candidate(
        "KXTESTSERIES", f"{code} test series", "Sports", ("Football",), None, None, ()
    )
    props = propose([by_ticker, by_title], _teams(), set())
    for c in (by_ticker, by_title):
        assert props[c.ticker] == ("exclude", ["other_league"]), (code, c.ticker)


def test_league_codes_do_not_match_inside_words_of_titles() -> None:
    c = Candidate("KXTESTSERIES", "Test MLSX series", "Sports", (), None, None, ())
    assert "other_league" not in propose([c], _teams(), set())[c.ticker][1]


def test_nfl_prefixes_and_combos_are_included() -> None:
    props = _proposals()
    for t in ("KXNFLGAME", *[t for t in props if t.startswith("KXMVENFL")]):
        if BY_TICKER[t].get("category") in ("Sports", "Exotics"):
            assert props[t][0] == "include", (t, props[t])


def test_team_name_in_title_is_included() -> None:
    props = _proposals()
    hits = [
        t
        for t, (p, rules) in props.items()
        if "nfl_team_in_title" in rules and not t.startswith(("KXNFL", "KXMVENFL"))
    ]
    assert hits, "expected a team-named series without an NFL ticker prefix"
    for t in hits:
        title = (BY_TICKER[t].get("title") or "").casefold()
        assert any(name.casefold() in title for name in _teams()), t


def test_non_sports_categories_are_excluded() -> None:
    props = _proposals()
    for t, (p, rules) in props.items():
        if BY_TICKER[t].get("category") not in ("Sports", "Exotics") and "non_sports" in rules:
            assert p in ("exclude", "undecided"), t


def test_conflicting_rules_leave_it_undecided() -> None:
    props = _proposals()
    for t, (p, rules) in props.items():
        includes = {"nfl_prefix", "fee_schedule_nfl", "nfl_team_in_title"} & set(rules)
        excludes = {"other_league", "non_sports"} & set(rules)
        if includes and excludes:
            assert p == "undecided", (t, rules)


def test_writing_proposals_never_approves_anything(tmp_path: Path) -> None:
    review = tmp_path / "kalshi_nfl_series.yaml"
    update_review_file(review, nfl_candidates(_series()))
    write_proposals(review, _proposals())
    data = yaml.safe_load(review.read_text(encoding="utf-8"))
    assert {r["decision"] for r in data["series"].values()} == {"pending"}
    assert all("proposed" in r and r["proposed_rules"] for r in data["series"].values())
    assert approved_series(review) == set()
