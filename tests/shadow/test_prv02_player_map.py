"""PRV-02 player map: a Kalshi player maps to an nflverse gsis_id only by an exact, unique match
of normalised name and team against rosters_weekly full_name at as_of.

Rulings 2026-11-21 (session 3): the roster week is chosen per team (the game week if the pull
read at as_of has that team's rows for it, else the team's latest earlier week of the season);
a unique match with no gsis_id is unmapped as no_gsis_id; with no pull at or before as_of the
earliest pull is read through the BT-01 snapshot rule (visible_weekly); punctuation is deleted
and the suffixes are dropped as whole words anywhere in the name.

Every name and code here is made up.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import polars as pl
import pytest

from ge.config import load_params
from ge.pricer_v0.player_map import (
    PlayerMapping,
    RosterAsOf,
    Unmapped,
    map_player,
    normalise_name,
    roster_as_of,
)
from ge.pricer_v0.teams import (
    GameNotMatched,
    KalshiGame,
    ScheduleGame,
    TeamMapError,
    game_of_event,
    parse_prop_event,
)
from ge.store import known_at as ka

UTC = dt.UTC
PULL = dt.datetime(2026, 11, 20, 14, 2, 30, tzinfo=UTC)
TEAM_MAP = {"KAA": "AA", "BB": "BB", "CC": "CC"}


# ---- normalisation ----


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Alpha Tester", "alpha tester"),
        ("ALPHA TESTER", "alpha tester"),
        ("  Alpha   Tester ", "alpha tester"),
        ("Alpha\tTester", "alpha tester"),
        ("Àlphà Tëstér", "alpha tester"),
        ("Ålpha Teşter", "alpha tester"),
        ("A.J. Tester", "aj tester"),
        ("AJ Tester", "aj tester"),
        ("D'Tester Alpha", "dtester alpha"),
        ("D\u2019Tester Alpha", "dtester alpha"),
        ("Alpha Tester-Beta", "alpha testerbeta"),
        ("Alpha Tester Jr.", "alpha tester"),
        ("Alpha Tester, Jr.", "alpha tester"),
        ("Alpha Tester Jr", "alpha tester"),
        ("Alpha Tester Sr.", "alpha tester"),
        ("Alpha Tester II", "alpha tester"),
        ("Alpha Tester III", "alpha tester"),
        ("Alpha Tester IV", "alpha tester"),
        ("Alpha Jr. Tester", "alpha tester"),
        ("Alpha Tester Junior", "alpha tester junior"),
        ("Ivan Siira Tester", "ivan siira tester"),
        ("Alpha Tester V", "alpha tester v"),
    ],
)
def test_normalise_name(raw: str, expected: str) -> None:
    assert normalise_name(raw) == expected


# ---- matching against a roster ----

COLS = ("season", "week", "team", "full_name", "gsis_id", "position")


def _rows(*rows: tuple[int, str, str, str | None, str]) -> pl.DataFrame:
    """(week, team, full_name, gsis_id, position) rows of season 2026."""
    return pl.DataFrame(
        [(2026, *r) for r in rows],
        schema={
            "season": pl.Int32,
            "week": pl.Int32,
            "team": pl.Utf8,
            "full_name": pl.Utf8,
            "gsis_id": pl.Utf8,
            "position": pl.Utf8,
        },
        orient="row",
    )


def _roster(df: pl.DataFrame) -> RosterAsOf:
    return RosterAsOf(season=2026, rows=df, pulled_at=PULL, label="rosters_weekly/2026@test")


ROSTER = _roster(
    _rows(
        (10, "AA", "Alpha Tester Jr.", "00-0000001", "WR"),
        (10, "AA", "Beta Tester", "00-0000002", "RB"),
        (10, "AA", "Gamma Twin", "00-0000003", "WR"),
        (10, "AA", "Gamma Twin", "00-0000004", "TE"),
        (10, "BB", "Beta Tester", "00-0000005", "WR"),
        (10, "BB", "Delta Nogsis", None, "RB"),
        (10, "BB", "Eps Clash", None, "RB"),
        (10, "BB", "Eps Clash", "00-0000006", "WR"),
        (11, "AA", "Alpha Tester Jr.", "00-0000001", "WR"),
    )
)


def test_unique_match_is_mapped_with_what_was_used() -> None:
    out = map_player("A.lpha Tester", "KAA", 11, ROSTER, TEAM_MAP)
    assert out == PlayerMapping(
        mapped=True,
        reason=None,
        gsis_id="00-0000001",
        position="WR",
        nflverse_team="AA",
        roster_week=11,
        roster_pulled_at=PULL,
        roster_label="rosters_weekly/2026@test",
        matches=1,
    )


def test_suffix_on_one_side_only_still_matches() -> None:
    out = map_player("Alpha Tester", "KAA", 11, ROSTER, TEAM_MAP)
    assert out.mapped and out.gsis_id == "00-0000001"


def test_same_name_on_two_teams_maps_by_team() -> None:
    assert map_player("Beta Tester", "KAA", 10, ROSTER, TEAM_MAP).gsis_id == "00-0000002"
    assert map_player("Beta Tester", "BB", 10, ROSTER, TEAM_MAP).gsis_id == "00-0000005"


def test_code_not_in_the_team_map_is_team_unmapped() -> None:
    out = map_player("Alpha Tester", "ZZ", 11, ROSTER, TEAM_MAP)
    assert (out.mapped, out.reason, out.gsis_id, out.nflverse_team) == (
        False,
        Unmapped.TEAM_UNMAPPED,
        None,
        None,
    )


def test_kalshi_code_is_not_used_as_an_nflverse_team() -> None:
    """KAA is Kalshi's code for nflverse AA; a roster team literally named KAA is not read."""
    df = pl.concat([ROSTER.rows, _rows((11, "KAA", "Zeta Wrongteam", "00-0000099", "WR"))])
    out = map_player("Zeta Wrongteam", "KAA", 11, _roster(df), TEAM_MAP)
    assert out.reason is Unmapped.NO_MATCH


def test_no_name_match_is_no_match() -> None:
    out = map_player("Omega Nobody", "KAA", 11, ROSTER, TEAM_MAP)
    assert (out.mapped, out.reason, out.matches, out.roster_week) == (
        False,
        Unmapped.NO_MATCH,
        0,
        11,
    )


def test_two_players_with_one_name_on_a_team_is_multiple_matches() -> None:
    out = map_player("Gamma Twin", "KAA", 10, ROSTER, TEAM_MAP)
    assert (out.mapped, out.reason, out.matches, out.gsis_id) == (
        False,
        Unmapped.MULTIPLE_MATCHES,
        2,
        None,
    )


def test_only_match_without_gsis_id_is_no_gsis_id() -> None:
    out = map_player("Delta Nogsis", "BB", 10, ROSTER, TEAM_MAP)
    assert (out.mapped, out.reason, out.matches) == (False, Unmapped.NO_GSIS_ID, 1)


def test_row_without_gsis_id_still_makes_a_name_ambiguous() -> None:
    out = map_player("Eps Clash", "BB", 10, ROSTER, TEAM_MAP)
    assert (out.reason, out.matches) == (Unmapped.MULTIPLE_MATCHES, 2)


def test_reason_codes() -> None:
    assert [u.value for u in Unmapped] == [
        "team_unmapped",
        "no_match",
        "multiple_matches",
        "no_gsis_id",
    ]


# ---- which roster week ----

WEEKS = _roster(
    _rows(
        (4, "AA", "Alpha Tester", "00-0000001", "WR"),
        (5, "BB", "Beta Tester", "00-0000002", "WR"),
        (6, "CC", "Gamma Tester", "00-0000003", "WR"),
        (7, "CC", "Gamma Tester", "00-0000003", "TE"),
        (8, "CC", "Gamma Tester", "00-0000003", "RB"),
        (2, "BB", "Old Tester", "00-0000004", "WR"),
    )
)


def test_game_week_is_used_when_the_team_has_rows_for_it() -> None:
    out = map_player("Gamma Tester", "CC", 7, WEEKS, TEAM_MAP)
    assert (out.roster_week, out.position) == (7, "TE")


def test_latest_earlier_week_is_chosen_per_team() -> None:
    """Game week 6: AA's latest week is 4 (bye in 5), BB's is 5. Later weeks are never read."""
    assert map_player("Alpha Tester", "KAA", 6, WEEKS, TEAM_MAP).roster_week == 4
    assert map_player("Beta Tester", "BB", 6, WEEKS, TEAM_MAP).roster_week == 5
    assert map_player("Gamma Tester", "CC", 5, WEEKS, TEAM_MAP).reason is Unmapped.NO_MATCH


def test_only_the_chosen_week_is_searched() -> None:
    """A player only on BB's week-2 roster is no longer matched once BB's week 5 is read."""
    out = map_player("Old Tester", "BB", 6, WEEKS, TEAM_MAP)
    assert (out.reason, out.roster_week) == (Unmapped.NO_MATCH, 5)


def test_team_with_no_rows_up_to_the_game_week_is_no_match() -> None:
    out = map_player("Gamma Tester", "CC", 3, WEEKS, TEAM_MAP)
    assert (out.reason, out.roster_week) == (Unmapped.NO_MATCH, None)


def test_player_who_changed_teams() -> None:
    """On AA up to week 5, on BB from week 6."""
    r = _roster(
        _rows(
            (5, "AA", "Moved Tester", "00-0000007", "WR"),
            (5, "BB", "Stay Tester", "00-0000008", "WR"),
            (6, "AA", "Stay Tester2", "00-0000009", "WR"),
            (6, "BB", "Moved Tester", "00-0000007", "WR"),
        )
    )
    assert map_player("Moved Tester", "BB", 6, r, TEAM_MAP).gsis_id == "00-0000007"
    assert map_player("Moved Tester", "KAA", 6, r, TEAM_MAP).reason is Unmapped.NO_MATCH
    # Week 7 not pulled yet: week 6 is read, so the new team matches and the old doesn't.
    assert map_player("Moved Tester", "BB", 7, r, TEAM_MAP).roster_week == 6
    assert map_player("Moved Tester", "KAA", 7, r, TEAM_MAP).reason is Unmapped.NO_MATCH
    # Week-5 game: he was still on AA.
    assert map_player("Moved Tester", "KAA", 5, r, TEAM_MAP).mapped
    assert map_player("Moved Tester", "BB", 5, r, TEAM_MAP).reason is Unmapped.NO_MATCH


def test_season_other_than_the_rosters_raises() -> None:
    with pytest.raises(ValueError, match="season"):
        map_player("Alpha Tester", "KAA", 11, RosterAsOf(2025, ROSTER.rows, PULL, "x"), TEAM_MAP)


# ---- reading rosters_weekly at as_of ----


def _ts(t: dt.datetime) -> str:
    return t.strftime("%Y%m%dT%H%M%SZ")


def _store(root: Path, dataset: str, pulled: dt.datetime, df: pl.DataFrame) -> None:
    d = root / dataset / "season=2026" / f"pulled_at={_ts(pulled)}"
    d.mkdir(parents=True)
    df.with_columns(pl.lit(pulled).alias("pulled_at")).write_parquet(d / "part.parquet")


SCHED = pl.DataFrame(
    {
        "game_id": ["2026_01_BB_AA", "2026_02_AA_BB"],
        "season": [2026, 2026],
        "game_type": ["REG", "REG"],
        "week": [1, 2],
        "gameday": ["2026-09-13", "2026-09-20"],
        "gametime": ["13:00", "13:00"],
        "away_team": ["BB", "AA"],
        "home_team": ["AA", "BB"],
    },
    schema_overrides={"season": pl.Int32, "week": pl.Int32},  # as nflverse stores them
)
P1 = dt.datetime(2026, 10, 1, 12, tzinfo=UTC)
P2 = dt.datetime(2026, 10, 8, 12, tzinfo=UTC)


@pytest.fixture
def store(tmp_path: Path) -> Path:
    _store(tmp_path, "schedules", P1, SCHED)
    _store(
        tmp_path,
        "rosters_weekly",
        P1,
        _rows(
            (1, "AA", "Alpha Tester", "00-0000001", "WR"),
            (2, "AA", "Alpha Tester", "00-0000001", "TE"),
        ),
    )
    _store(
        tmp_path,
        "rosters_weekly",
        P2,
        _rows(
            (1, "AA", "Alpha Tester", "00-0000001", "RB"),
            (2, "AA", "Alpha Tester", "00-0000001", "RB"),
        ),
    )
    return tmp_path


def test_latest_pull_at_or_before_as_of_is_read(store: Path) -> None:
    r = roster_as_of(2026, P2 - dt.timedelta(seconds=1), root=store)
    assert r.pulled_at == P1 and set(r.rows["position"]) == {"WR", "TE"}
    assert "rosters_weekly/2026@20261001T120000Z" in r.label
    r2 = roster_as_of(2026, P2, root=store)
    assert r2.pulled_at == P2 and set(r2.rows["position"]) == {"RB"}


def test_mapping_records_the_pull_read(store: Path) -> None:
    out = map_player("Alpha Tester", "KAA", 2, roster_as_of(2026, P2, root=store), TEAM_MAP)
    assert (out.roster_pulled_at, out.roster_week, out.position) == (P2, 2, "RB")


def test_before_the_first_pull_uses_the_snapshot_rule(store: Path) -> None:
    """BT-01 snapshot rule: the earliest pull, team-weeks whose assumed report time <= as_of."""
    bt = load_params().backtest
    tw = ka.team_weeks(SCHED, bt)
    wk2 = tw.filter((pl.col("week") == 2) & (pl.col("team") == "AA"))["known_at"][0]
    r = roster_as_of(2026, wk2 - dt.timedelta(seconds=1), root=store, bt=bt)
    assert r.pulled_at == P1 and r.rows["week"].to_list() == [1]
    assert "vintage_after_as_of" in r.label and "assumed known" in r.label
    assert roster_as_of(2026, wk2, root=store, bt=bt).rows["week"].to_list() == [1, 2]


def test_no_rosters_weekly_pull_raises(tmp_path: Path) -> None:
    _store(tmp_path, "schedules", P1, SCHED)
    with pytest.raises(FileNotFoundError, match="rosters_weekly"):
        roster_as_of(2026, P2, root=tmp_path)


def test_naive_as_of_raises(store: Path) -> None:
    with pytest.raises(ValueError, match="timezone"):
        roster_as_of(2026, dt.datetime(2026, 10, 9), root=store)


# ---- the game a prop event is for ----

CODES = frozenset({"KAA", "BB", "CC"})
GAMES = [
    ScheduleGame("2026_11_BB_AA", 2026, 11, dt.date(2026, 11, 22), "BB", "AA"),
    ScheduleGame("2026_12_CC_AA", 2026, 12, dt.date(2026, 11, 29), "CC", "AA"),
]


def test_parse_prop_event() -> None:
    assert parse_prop_event("KXNFLREC-26NOV22BBKAA", CODES) == KalshiGame(
        "KXNFLREC-26NOV22BBKAA", dt.date(2026, 11, 22), ("BB", "KAA")
    )
    for series in ("KXNFLRECYDS", "KXNFLRSHYDS"):
        assert parse_prop_event(f"{series}-26NOV22BBKAA", CODES).codes == ("BB", "KAA")


@pytest.mark.parametrize(
    "ticker", ["KXNFLGAME-26NOV22BBKAA", "KXNFLREC-26NOV22BBKAA-BBX-5", "KXNFLREC-26NOV22BBZZ"]
)
def test_unparseable_prop_event_raises(ticker: str) -> None:
    with pytest.raises(TeamMapError):
        parse_prop_event(ticker, CODES)


def test_game_of_event_gives_the_week() -> None:
    g = game_of_event(parse_prop_event("KXNFLREC-26NOV22BBKAA", CODES), TEAM_MAP, GAMES)
    assert (g.game_id, g.week) == ("2026_11_BB_AA", 11)


def test_game_of_event_needs_the_same_date() -> None:
    with pytest.raises(GameNotMatched):
        game_of_event(parse_prop_event("KXNFLREC-26NOV23BBKAA", CODES), TEAM_MAP, GAMES)


def test_game_of_event_with_unmapped_code_raises() -> None:
    with pytest.raises(TeamMapError, match="KAA"):
        game_of_event(parse_prop_event("KXNFLREC-26NOV22BBKAA", CODES), {"BB": "BB"}, GAMES)
