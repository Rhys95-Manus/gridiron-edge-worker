"""PRV-02 team map: Kalshi team codes to nflverse abbreviations, derived by matching each 2026
KXNFLGAME event to the nflverse schedules game on the same date with the same two teams.

Synthetic tests use made-up codes (AA, BBB, ...). The real check re-derives the map from a
fixture saved from the 2026 raw store and compares it with config/kalshi_team_codes.yaml, so
the build fails if any code maps to no team, to two teams, or shares a team with another code.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pytest
import yaml

from ge.pricer_v0.scope import TEAM_CODES_PATH, load_team_codes
from ge.pricer_v0.teams import (
    GameNotMatched,
    KalshiGame,
    ScheduleGame,
    TeamMapError,
    derive_team_map,
    load_team_map,
    match_game,
    parse_game_event,
)
from tests.shadow.conftest import load_fixture

D1, D2, D3, D4 = (dt.date(2026, 11, d) for d in (1, 2, 8, 9))


def _g(gid: str, day: dt.date, away: str, home: str, week: int = 1) -> ScheduleGame:
    return ScheduleGame(
        game_id=gid, season=2026, week=week, gameday=day, away_team=away, home_team=home
    )


def _e(day: dt.date, a: str, b: str) -> KalshiGame:
    return KalshiGame(event_ticker=f"KXNFLGAME-x{a}{b}", date=day, codes=(a, b))


# Kalshi AA, BBB, CC, DD; nflverse AA, BB, CC, DD. BBB differs. Without D4 the swap
# AA<->CC, BBB<->DD would fit every event too; D4 (AA v DD) pins every code down.
CODES = frozenset({"AA", "BBB", "CC", "DD"})
GAMES = [
    _g("g1", D1, "AA", "BB"),
    _g("g2", D1, "CC", "DD"),
    _g("g3", D2, "AA", "CC"),
    _g("g4", D3, "BB", "DD"),
    _g("g5", D4, "AA", "DD"),
]
EVENTS = [
    _e(D1, "AA", "BBB"),
    _e(D1, "CC", "DD"),
    _e(D2, "AA", "CC"),
    _e(D3, "BBB", "DD"),
    _e(D4, "AA", "DD"),
]


# ---- parsing a KXNFLGAME event ----


def test_parse_game_event() -> None:
    codes = frozenset({"CIN", "WAS", "LA", "LAC", "KC"})
    g = parse_game_event("KXNFLGAME-26NOV23CINWAS", codes)
    assert g == KalshiGame("KXNFLGAME-26NOV23CINWAS", dt.date(2026, 11, 23), ("CIN", "WAS"))
    assert parse_game_event("KXNFLGAME-26JAN04LACKC", codes).codes == ("LAC", "KC")


@pytest.mark.parametrize(
    "ticker",
    [
        "KXNFLGAME-26NOV23CINWAS-WAS",  # a market ticker, not an event
        "KXNFLREC-26NOV23CINWAS",  # another series
        "KXNFLGAME-26XYZ23CINWAS",  # no such month
        "KXNFLGAME-26NOV31CINWAS",  # no such day
        "KXNFLGAME-26NOV23CINXXX",  # unknown code
    ],
)
def test_unparseable_event_raises(ticker: str) -> None:
    with pytest.raises(TeamMapError):
        parse_game_event(ticker, frozenset({"CIN", "WAS"}))


def test_event_whose_code_splits_two_ways_raises() -> None:
    with pytest.raises(TeamMapError, match="split"):
        parse_game_event("KXNFLGAME-26NOV23LACKC", frozenset({"LA", "CKC", "LAC", "KC"}))


# ---- deriving the map ----


def test_derive_maps_each_code_to_its_team() -> None:
    assert derive_team_map(EVENTS, GAMES, CODES) == {
        "AA": "AA",
        "BBB": "BB",
        "CC": "CC",
        "DD": "DD",
    }


def test_derive_ignores_home_and_away_order() -> None:
    flipped = [_e(e.date, e.codes[1], e.codes[0]) for e in EVENTS]
    assert derive_team_map(flipped, GAMES, CODES) == derive_team_map(EVENTS, GAMES, CODES)


def test_code_with_no_event_fails() -> None:
    with pytest.raises(TeamMapError, match="EE"):
        derive_team_map(EVENTS, GAMES, CODES | {"EE"})


def test_code_that_could_be_two_teams_fails() -> None:
    """One event, one game: AA and BBB could each be either team, so nothing is guessed."""
    with pytest.raises(TeamMapError, match="more than one"):
        derive_team_map([_e(D1, "AA", "BBB")], [_g("g1", D1, "XX", "YY")], frozenset({"AA", "BBB"}))


def test_two_codes_on_one_team_fails() -> None:
    """CC is pinned by D3 (CC v YY, DD v ZZ on another date). AA and AB each meet CC on a
    date when only XX-CC is played, so both would be XX."""
    games = [
        _g("g1", D1, "XX", "CC"),
        _g("g2", D2, "XX", "CC"),
        _g("g3", D3, "CC", "YY"),
        _g("g4", D4, "ZZ", "YY"),
    ]
    events = [_e(D1, "AA", "CC"), _e(D2, "AB", "CC"), _e(D3, "CC", "DD"), _e(D4, "EE", "DD")]
    with pytest.raises(TeamMapError, match="same nflverse team"):
        derive_team_map(events, games, frozenset({"AA", "AB", "CC", "DD", "EE"}))


def test_event_with_no_game_that_date_fails() -> None:
    with pytest.raises(TeamMapError, match="KXNFLGAME-xCCAA"):
        derive_team_map([*EVENTS, _e(D3, "CC", "AA")], GAMES, CODES)


def test_event_one_day_off_is_not_shifted() -> None:
    """A game listed a day later in schedules (a time-zone slip) is not matched."""
    games = [
        g if g.game_id != "g3" else _g("g3", D2 + dt.timedelta(days=1), "AA", "CC") for g in GAMES
    ]
    with pytest.raises(TeamMapError):
        derive_team_map(EVENTS, games, CODES)


# ---- matching one event's game ----


def test_match_game() -> None:
    assert match_game(D1, frozenset({"BB", "AA"}), GAMES).game_id == "g1"


@pytest.mark.parametrize(
    ("day", "teams"),
    [(D1, frozenset({"AA", "CC"})), (D2 + dt.timedelta(days=1), frozenset({"AA", "CC"}))],
)
def test_match_game_needs_same_date_and_teams(day: dt.date, teams: frozenset[str]) -> None:
    with pytest.raises(GameNotMatched):
        match_game(day, teams, GAMES)


def test_match_game_with_two_games_raises() -> None:
    with pytest.raises(GameNotMatched, match="2"):
        match_game(D1, frozenset({"AA", "BB"}), [*GAMES, _g("g9", D1, "BB", "AA")])


# ---- the config file ----


def _write(tmp_path: Path, nflverse: dict[str, Any]) -> Path:
    cfg = yaml.safe_load(TEAM_CODES_PATH.read_text(encoding="utf-8"))
    cfg["nflverse"] = nflverse
    p = tmp_path / "kalshi_team_codes.yaml"
    p.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return p


def _block() -> dict[str, Any]:
    cfg = yaml.safe_load(TEAM_CODES_PATH.read_text(encoding="utf-8"))
    block = cfg["nflverse"]
    assert isinstance(block, dict)
    return block


def test_config_map_covers_every_code_once() -> None:
    m = load_team_map()
    assert set(m) == load_team_codes() and len(m) == 32
    assert len(set(m.values())) == 32


def test_config_map_records_its_source() -> None:
    block = _block()
    fixture = load_fixture("kalshi_nflverse_games.json")
    assert block["spec_id"] == "PRV-02" and block["status"] == "initial"
    assert block["source"] == fixture["source"]
    assert block["pulled_at"] == fixture["pulled_at"]
    assert block["kalshi_pulled_at"] == fixture["kalshi_pulled_at"]


def test_config_map_is_what_the_2026_games_give() -> None:
    """PRV-02: the map is derived from matched games, not written by hand."""
    fixture = load_fixture("kalshi_nflverse_games.json")
    codes = load_team_codes()
    events = [parse_game_event(e, codes) for e in fixture["events"]]
    games = [ScheduleGame.from_row(r) for r in fixture["games"]]
    assert derive_team_map(events, games, codes) == load_team_map()


def test_config_map_with_a_shared_team_fails(tmp_path: Path) -> None:
    block = _block()
    teams = dict(block["teams"])
    a, b = sorted(teams)[:2]
    teams[b] = teams[a]
    with pytest.raises(ValueError, match="same nflverse team"):
        load_team_map(_write(tmp_path, {**block, "teams": teams}))


def test_config_map_missing_a_code_fails(tmp_path: Path) -> None:
    block = _block()
    teams = dict(block["teams"])
    teams.pop(sorted(teams)[0])
    with pytest.raises(ValueError, match="every Kalshi code"):
        load_team_map(_write(tmp_path, {**block, "teams": teams}))


def test_config_map_extra_code_fails(tmp_path: Path) -> None:
    block = _block()
    with pytest.raises(ValueError, match="every Kalshi code"):
        load_team_map(_write(tmp_path, {**block, "teams": {**block["teams"], "ZZZ": "ZZZ"}}))
