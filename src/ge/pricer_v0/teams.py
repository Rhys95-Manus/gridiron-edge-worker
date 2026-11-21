"""PRV-02 team map: Kalshi team codes to nflverse team abbreviations.

PRV-02: "Kalshi team codes map to nflverse team abbreviations through
config/kalshi_team_codes.yaml, derived by matching each 2026 KXNFLGAME event to the nflverse
schedules game on the same date with the same two teams; every Kalshi code must map to exactly
one nflverse team, or the build fails."

The date is the one in Kalshi's event ticker, compared with schedules' gameday as it stands (both
are US Eastern dates in the 2026 data); no time-zone shift is tried, so a game listed on another
day fails instead of being matched.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, StringConstraints

from ge.pricer_v0.scope import PRV01_SERIES, TEAM_CODES_PATH, load_team_codes, split_game_code

_EVENT = re.compile(
    r"^(?P<series>[A-Z0-9]+)-(?P<yy>\d{2})(?P<mon>[A-Z]{3})(?P<dd>\d{2})(?P<teams>[A-Z]+)$"
)
_MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
_Code = Annotated[str, StringConstraints(pattern=r"^[A-Z]+$")]


class TeamMapError(ValueError):
    """PRV-02: the Kalshi-to-nflverse team map can't be derived exactly."""


class GameNotMatched(LookupError):
    """PRV-02: no single nflverse schedules game on that date with those two teams."""


@dataclass(frozen=True)
class KalshiGame:
    """PRV-02: one KXNFLGAME event: its ticker, the date in it and its two Kalshi codes."""

    event_ticker: str
    date: dt.date
    codes: tuple[str, str]


@dataclass(frozen=True)
class ScheduleGame:
    """PRV-02: one nflverse schedules game (DATA-01): ID, season, week, Eastern date, teams."""

    game_id: str
    season: int
    week: int
    gameday: dt.date
    away_team: str
    home_team: str

    @property
    def teams(self) -> frozenset[str]:
        return frozenset((self.away_team, self.home_team))

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> ScheduleGame:
        """PRV-02: a schedules row (gameday as an ISO date string, as nflverse stores it)."""
        return cls(
            game_id=str(row["game_id"]),
            season=int(row["season"]),
            week=int(row["week"]),
            gameday=dt.date.fromisoformat(str(row["gameday"])),
            away_team=str(row["away_team"]),
            home_team=str(row["home_team"]),
        )


def _parse_event(event_ticker: str, codes: frozenset[str], series: tuple[str, ...]) -> KalshiGame:
    m = _EVENT.match(event_ticker)
    if m is None or m["series"] not in series or m["mon"] not in _MONTHS:
        raise TeamMapError(f"{event_ticker}: not an event ticker of {', '.join(series)}")
    try:
        date = dt.date(2000 + int(m["yy"]), _MONTHS.index(m["mon"]) + 1, int(m["dd"]))
    except ValueError as exc:
        raise TeamMapError(f"{event_ticker}: no such date") from exc
    pair = split_game_code(m["teams"], codes)
    if pair is None:
        raise TeamMapError(
            f"{event_ticker}: game code does not split into exactly one pair of Kalshi codes"
        )
    return KalshiGame(event_ticker=event_ticker, date=date, codes=pair)


def parse_game_event(event_ticker: str, codes: frozenset[str]) -> KalshiGame:
    """PRV-02: a KXNFLGAME event ticker, <series>-<yyMMMdd><team><team>, read with PRV-01's
    rule that the game code splits into exactly one pair of listed Kalshi codes."""
    return _parse_event(event_ticker, codes, ("KXNFLGAME",))


def parse_prop_event(event_ticker: str, codes: frozenset[str]) -> KalshiGame:
    """PRV-02: the game of a PRV-01 series event ticker (e.g. KXNFLREC-26NOV22ARIKC), read the
    same way as a KXNFLGAME event."""
    return _parse_event(event_ticker, codes, PRV01_SERIES)


def game_of_event(
    event: KalshiGame, team_map: Mapping[str, str], games: Iterable[ScheduleGame]
) -> ScheduleGame:
    """PRV-02: the schedules game an event is for (its season and week pick the roster week):
    same date, same two teams through the Kalshi -> nflverse map. A code missing from the map
    raises TeamMapError; no single matching game raises GameNotMatched."""
    missing = [c for c in event.codes if c not in team_map]
    if missing:
        raise TeamMapError(f"{event.event_ticker}: codes not in the team map: {missing}")
    return match_game(event.date, frozenset(team_map[c] for c in event.codes), games)


def match_game(date: dt.date, teams: frozenset[str], games: Iterable[ScheduleGame]) -> ScheduleGame:
    """PRV-02: the one schedules game on the same date with the same two nflverse teams."""
    hits = [g for g in games if g.gameday == date and g.teams == teams]
    if len(hits) != 1:
        raise GameNotMatched(
            f"{len(hits)} schedules games on {date.isoformat()} with {sorted(teams)}"
        )
    return hits[0]


def _roles(day: list[ScheduleGame], a: set[str], b: set[str]) -> tuple[set[str], set[str]]:
    """Teams each side can be: games that day with one team allowed for a, the other for b."""
    na: set[str] = set()
    nb: set[str] = set()
    for g in day:
        for x, y in ((g.away_team, g.home_team), (g.home_team, g.away_team)):
            if x in a and y in b:
                na.add(x)
                nb.add(y)
    return na, nb


def derive_team_map(
    events: Iterable[KalshiGame], games: Iterable[ScheduleGame], codes: frozenset[str]
) -> dict[str, str]:
    """PRV-02: each Kalshi code's nflverse team, from matching every KXNFLGAME event to the
    schedules game on the same date with the same two teams.

    A code's possible teams start as every schedules team and are narrowed, event by event,
    to the teams it could be in a game played that date against a team its opponent could be,
    until nothing changes. The map is returned only if every code then has exactly one team,
    no two codes share one, and every event matches exactly one game; otherwise TeamMapError
    lists every problem."""
    evs = sorted(set(events), key=lambda e: e.event_ticker)
    gms = list(games)
    by_date: dict[dt.date, list[ScheduleGame]] = defaultdict(list)
    for g in gms:
        by_date[g.gameday].append(g)
    all_teams = {t for g in gms for t in g.teams}
    cand = {c: set(all_teams) for c in codes}
    problems: list[str] = []
    unknown = sorted({c for e in evs for c in e.codes} - codes)
    if unknown:
        raise TeamMapError(f"events use codes not in the Kalshi list: {unknown}")

    changed = True
    while changed:
        changed = False
        for e in evs:
            a, b = e.codes
            na, nb = _roles(by_date.get(e.date, []), cand[a], cand[b])
            if na != cand[a] or nb != cand[b]:
                cand[a], cand[b] = na, nb
                changed = True

    no_fit = [
        e.event_ticker
        for e in evs
        if not _roles(by_date.get(e.date, []), cand[e.codes[0]], cand[e.codes[1]])[0]
    ]
    if no_fit:
        problems.append(f"events with no schedules game that date that fits: {no_fit}")
    seen = {c for e in evs for c in e.codes}
    if missing := sorted(codes - seen):
        problems.append(f"codes in no KXNFLGAME event: {missing}")
    if none := sorted(c for c in seen if not cand[c]):
        problems.append(f"codes with no nflverse team: {none}")
    if many := sorted(c for c in seen if len(cand[c]) > 1):
        problems.append(f"codes that could be more than one nflverse team: {many}")
    mapping = {c: next(iter(t)) for c, t in sorted(cand.items()) if c in seen and len(t) == 1}
    by_team: dict[str, list[str]] = defaultdict(list)
    for c, t in mapping.items():
        by_team[t].append(c)
    if shared := {t: cs for t, cs in sorted(by_team.items()) if len(cs) > 1}:
        problems.append(f"codes mapped to the same nflverse team: {shared}")
    if not problems:
        unmatched = []
        for e in evs:
            try:
                match_game(e.date, frozenset(mapping[c] for c in e.codes), by_date[e.date])
            except GameNotMatched:
                unmatched.append(e.event_ticker)
        if unmatched:
            problems.append(f"events matching no single schedules game: {unmatched}")
    if problems:
        raise TeamMapError("; ".join(problems))
    return mapping


class _TeamMap(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    spec_id: Literal["PRV-02"]
    status: Literal["initial"]
    source: Annotated[str, StringConstraints(min_length=1)]
    pulled_at: Annotated[str, StringConstraints(min_length=1)]
    kalshi_pulled_at: Annotated[str, StringConstraints(min_length=1)]
    teams: dict[_Code, _Code]


def load_team_map(path: Path = TEAM_CODES_PATH) -> dict[str, str]:
    """PRV-02: Kalshi code -> nflverse abbreviation from config/kalshi_team_codes.yaml. Fails
    unless every Kalshi code is listed exactly once and no two codes share an nflverse team."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "nflverse" not in raw:
        raise ValueError(f"{path}: no nflverse block (PRV-02)")
    cfg = _TeamMap.model_validate(raw["nflverse"])
    codes = load_team_codes(path)
    if set(cfg.teams) != codes:
        raise ValueError(f"{path}: the nflverse map must list every Kalshi code exactly once")
    by_team: dict[str, list[str]] = defaultdict(list)
    for c, t in cfg.teams.items():
        by_team[t].append(c)
    if shared := {t: cs for t, cs in by_team.items() if len(cs) > 1}:
        raise ValueError(f"{path}: Kalshi codes mapped to the same nflverse team: {shared}")
    return dict(sorted(cfg.teams.items()))
