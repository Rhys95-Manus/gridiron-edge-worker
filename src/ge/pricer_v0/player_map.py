"""PRV-02 player map: a Kalshi player to an nflverse gsis_id, never guessed.

PRV-02: "A Kalshi player maps to an nflverse gsis_id only by an exact, unique match of
normalised name and team code against rosters_weekly at as_of. Names are normalised by
lower-casing, removing accents and punctuation, dropping the suffixes Jr, Sr, II, III and IV,
and collapsing spaces. Anything else is logged unpriced as unmapped, never guessed." Player
names are matched against rosters_weekly full_name only; the Kalshi team code goes through
config/kalshi_team_codes.yaml (ge.pricer_v0.teams).

Rulings 2026-11-21 (session 3):
- Roster week, per team: the game's week if the rosters_weekly pull read at as_of has the
  team's rows for it, otherwise the team's latest earlier week of the same season.
- The pull read is the BT-01 one (latest at or before as_of); before our first pull of the
  season, the earliest pull through the snapshot's weekly-report rule (visible_weekly).
- A unique match whose row has no gsis_id is unmapped as no_gsis_id; such a row still counts
  as a match, so it can make a name ambiguous.
- Punctuation (Unicode categories P*) is deleted, not replaced by a space; the suffixes are
  dropped as whole words wherever they appear.
"""

from __future__ import annotations

import datetime as dt
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl

from ge.config import Backtest, load_params
from ge.ingest.raw import DATA_ROOT
from ge.store import known_at as ka
from ge.store.vintage import choose_version

# PRV-02: "dropping the suffixes Jr, Sr, II, III and IV" (compared after lower-casing).
_SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv"})
ROSTER_COLUMNS = ("season", "week", "team", "full_name", "gsis_id", "position")


class Unmapped(StrEnum):
    """PRV-02 unmapped sub-reasons (the market is unpriced as unmapped)."""

    TEAM_UNMAPPED = "team_unmapped"
    NO_MATCH = "no_match"
    MULTIPLE_MATCHES = "multiple_matches"
    NO_GSIS_ID = "no_gsis_id"


@dataclass(frozen=True)
class RosterAsOf:
    """PRV-02: one season's rosters_weekly rows as known at as_of, and the pull they came from."""

    season: int
    rows: pl.DataFrame
    pulled_at: dt.datetime
    label: str


@dataclass(frozen=True)
class PlayerMapping:
    """PRV-02: the mapping verdict and what it used. gsis_id and position only when mapped."""

    mapped: bool
    reason: Unmapped | None
    gsis_id: str | None
    position: str | None
    nflverse_team: str | None
    roster_week: int | None
    roster_pulled_at: dt.datetime | None
    roster_label: str | None
    matches: int


def normalise_name(name: str) -> str:
    """PRV-02: lower-case, remove accents and punctuation, drop the suffixes Jr, Sr, II, III and
    IV, collapse spaces. The same function is applied to Kalshi's and nflverse's names."""
    s = name.lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = "".join(c for c in s if not unicodedata.category(c).startswith("P"))
    return " ".join(w for w in s.split() if w not in _SUFFIXES)


def roster_as_of(
    season: int, as_of: dt.datetime, *, root: Path = DATA_ROOT, bt: Backtest | None = None
) -> RosterAsOf:
    """PRV-02 / BT-01: the season's rosters_weekly rows known at as_of: the latest pull at or
    before as_of, or, before our first pull, the earliest pull limited to team-weeks whose
    assumed report time is at or before as_of (the snapshot's rule)."""
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    as_of = as_of.astimezone(dt.UTC)
    v = choose_version(root, "rosters_weekly", season, as_of)
    if v is None:
        raise FileNotFoundError(f"no {season} rosters_weekly pull under {root}")
    rows = pl.read_parquet(v.path, columns=list(ROSTER_COLUMNS))
    label = v.label
    if v.after_as_of:
        bt = bt or load_params().backtest
        sv = choose_version(root, "schedules", season, as_of)
        if sv is None:
            raise FileNotFoundError(f"no {season} schedules pull under {root}")
        tw = ka.team_weeks(pl.read_parquet(sv.path), bt)
        rows = ka.visible_weekly(rows, tw, as_of, "team")
        label += (
            f"; no publish time before our own pulls; assumed known at "
            f"{int(bt.bt_01_assumed_report_hour_et.value)}:00 ET, "
            f"{int(bt.bt_01_assumed_report_days_before_kickoff.value)} day(s) before the "
            "team's kickoff (stated assumption, BT-01)"
        )
    return RosterAsOf(season=season, rows=rows, pulled_at=v.pulled_at, label=label)


def map_player(
    name: str, kalshi_team: str, week: int, roster: RosterAsOf, team_map: Mapping[str, str]
) -> PlayerMapping:
    """PRV-02: map Kalshi's player name and team code for a game in `week` of roster.season.
    Exactly one (normalised full_name, nflverse team) match in the team's roster week is
    mapped; anything else is unmapped with its sub-reason."""
    seasons = set(roster.rows["season"].unique().to_list())
    if seasons - {roster.season}:
        raise ValueError(f"roster rows of season {sorted(seasons)}, expected {roster.season}")

    def verdict(
        reason: Unmapped | None,
        team: str | None = None,
        used: int | None = None,
        matches: int = 0,
        gsis_id: str | None = None,
        position: str | None = None,
    ) -> PlayerMapping:
        return PlayerMapping(
            mapped=reason is None,
            reason=reason,
            gsis_id=gsis_id,
            position=position,
            nflverse_team=team,
            roster_week=used,
            roster_pulled_at=roster.pulled_at,
            roster_label=roster.label,
            matches=matches,
        )

    team = team_map.get(kalshi_team)
    if team is None:
        return verdict(Unmapped.TEAM_UNMAPPED)
    mine = roster.rows.filter((pl.col("team") == team) & (pl.col("week") <= week))
    if mine.is_empty():
        return verdict(Unmapped.NO_MATCH, team)
    weeks = set(mine["week"].to_list())
    used = week if week in weeks else max(weeks)
    key = normalise_name(name)
    hits = [
        r
        for r in mine.filter(pl.col("week") == used).iter_rows(named=True)
        if r["full_name"] is not None and normalise_name(r["full_name"]) == key
    ]
    if not hits:
        return verdict(Unmapped.NO_MATCH, team, used)
    if len(hits) > 1:
        return verdict(Unmapped.MULTIPLE_MATCHES, team, used, len(hits))
    hit = hits[0]
    if hit["gsis_id"] is None:
        return verdict(Unmapped.NO_GSIS_ID, team, used, 1)
    return verdict(None, team, used, 1, hit["gsis_id"], hit["position"])
