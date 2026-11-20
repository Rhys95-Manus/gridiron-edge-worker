"""PRV-01 market scope: which Kalshi player-prop markets pricer v0 prices.

Reads one market as Kalshi's public API returns it (DATA-08; the raw_json column of
kalshi_markets) and says whether it is in scope, with the fields the pricer needs. Nothing
outside PRV-01 is guessed: such a market is unpriced with a reason code.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from ge.config import REPO_ROOT, load_params

# PRV-01: "the series KXNFLRECYDS, KXNFLRSHYDS and KXNFLREC".
PRV01_SERIES = ("KXNFLRECYDS", "KXNFLRSHYDS", "KXNFLREC")
# Kalshi's title for each series, "<player>: <X>+ <stat>" (DATA-08, as in the fixtures).
_TITLE_STAT = {
    "KXNFLRECYDS": "receiving yards",
    "KXNFLRSHYDS": "rushing yards",
    "KXNFLREC": "receptions",
}
# <series>-<yyMMMdd><away><home>-<team><player>-<X>, e.g. KXNFLREC-26NOV22ARIKC-KCPLAYER04-3.
_TICKER = re.compile(
    r"^(?P<series>[A-Z0-9]+)-(?P<game>(?P<date>\d{2}[A-Z]{3}\d{2})(?P<teams>[A-Z]+))"
    r"-(?P<player>[A-Z0-9]+)-(?P<x>\d+)$"
)
TEAM_CODES_PATH = REPO_ROOT / "config" / "kalshi_team_codes.yaml"


class Unpriced(StrEnum):
    """PRV-01 reason codes, in the order they are checked; the first failure is reported.
    series_missing to strike_not_whole are PRV-01's own tests; ticker_unparsed to
    team_code_unparsed are fields the pricer needs that did not parse or agree (ruling
    2026-11-19: own codes, kept apart from PRV-01's)."""

    SERIES_MISSING = "series_missing"
    SERIES_OUT_OF_SCOPE = "series_out_of_scope"
    STRIKE_TYPE_MISSING = "strike_type_missing"
    STRIKE_TYPE_NOT_GREATER = "strike_type_not_greater"
    CAP_STRIKE_SET = "cap_strike_set"
    FLOOR_STRIKE_MISSING = "floor_strike_missing"
    FLOOR_STRIKE_NOT_NUMERIC = "floor_strike_not_numeric"
    STRIKE_NOT_WHOLE = "strike_not_whole"
    TICKER_UNPARSED = "ticker_unparsed"
    X_MISMATCH = "x_mismatch"
    TITLE_UNPARSED = "title_unparsed"
    PLAYER_UUID_MISSING = "player_uuid_missing"
    TEAM_CODE_UNPARSED = "team_code_unparsed"


@dataclass(frozen=True)
class ScopedMarket:
    """PRV-01: one market and its scope verdict. Fields that do not parse exactly are None;
    a market is priced only when reason is None."""

    ticker: str | None
    event_ticker: str | None
    series: str | None
    x: int | None
    floor_strike: float | None
    strike_type: str | None
    cap_strike: object
    player_uuid: str | None
    team_uuid: str | None
    player_name: str | None
    team_code: str | None
    priced: bool
    reason: Unpriced | None


class _TeamCodes(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    spec_id: Literal["PRV-01"]
    status: Literal["initial"]
    source: Annotated[str, StringConstraints(min_length=1)]
    pulled_at: Annotated[str, StringConstraints(min_length=1)]
    codes: Annotated[
        list[Annotated[str, StringConstraints(pattern=r"^[A-Z]+$")]], Field(min_length=2)
    ]


def load_team_codes(path: Path = TEAM_CODES_PATH) -> frozenset[str]:
    """PRV-01: Kalshi's NFL team codes (config/kalshi_team_codes.yaml, ruling 2026-11-19)."""
    cfg = _TeamCodes.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    if len(set(cfg.codes)) != len(cfg.codes):
        raise ValueError(f"{path}: duplicate team codes")
    return frozenset(cfg.codes)


def _str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _team_code(teams: str, player: str, codes: frozenset[str]) -> str | None:
    """PRV-01: the player's team code. The game code must split into exactly one pair of
    listed codes, and the player segment must start with exactly one of the two."""
    splits = [
        (teams[:i], teams[i:])
        for i in range(1, len(teams))
        if teams[:i] in codes and teams[i:] in codes
    ]
    if len(splits) != 1:
        return None
    hits = [c for c in splits[0] if player.startswith(c) and len(player) > len(c)]
    return hits[0] if len(hits) == 1 else None


def scope_market(market: Mapping[str, Any], team_codes: frozenset[str]) -> ScopedMarket:
    """PRV-01: Pricer v0 prices only markets in the series KXNFLRECYDS, KXNFLRSHYDS and
    KXNFLREC with strike_type "greater", no cap_strike, and floor_strike + 0.5 a whole number.
    YES means the stat is at least X = floor_strike + 0.5. Every other market in those events
    is logged unpriced with its reason.

    A cap_strike that is absent or null is "no cap_strike". The ticker's X, the title's X and
    floor_strike + 0.5 must agree, and the title must read "<player>: <X>+ <stat>" for the
    market's series."""
    offset = float(load_params().pricer_v0.prv_01_strike_offset.value)
    failures: list[Unpriced] = []

    series = _str(market.get("series_ticker"))
    if series is None:
        failures.append(Unpriced.SERIES_MISSING)
    elif series not in PRV01_SERIES:
        failures.append(Unpriced.SERIES_OUT_OF_SCOPE)

    strike_type = _str(market.get("strike_type"))
    if "strike_type" not in market or market["strike_type"] is None:
        failures.append(Unpriced.STRIKE_TYPE_MISSING)
    elif strike_type != "greater":
        failures.append(Unpriced.STRIKE_TYPE_NOT_GREATER)

    cap_strike = market.get("cap_strike")
    if cap_strike is not None:
        failures.append(Unpriced.CAP_STRIKE_SET)

    raw_floor = market.get("floor_strike")
    floor_strike: float | None = None
    x: int | None = None
    if raw_floor is None:
        failures.append(Unpriced.FLOOR_STRIKE_MISSING)
    elif not _is_number(raw_floor):
        failures.append(Unpriced.FLOOR_STRIKE_NOT_NUMERIC)
    else:
        floor_strike = float(raw_floor)
        if (floor_strike + offset).is_integer():
            x = int(floor_strike + offset)
        else:
            failures.append(Unpriced.STRIKE_NOT_WHOLE)

    ticker = _str(market.get("ticker"))
    event_ticker = _str(market.get("event_ticker"))
    m = _TICKER.match(ticker) if ticker is not None else None
    if m is None or m["series"] != series or event_ticker != f"{m['series']}-{m['game']}":
        m = None
        failures.append(Unpriced.TICKER_UNPARSED)
    elif x is not None and int(m["x"]) != x:
        failures.append(Unpriced.X_MISMATCH)

    player_name: str | None = None
    title = _str(market.get("title"))
    stat = _TITLE_STAT.get(series or "")
    t = (
        re.fullmatch(rf"(?P<name>\S.*\S|\S): (?P<x>\d+)\+ {re.escape(stat)}", title)
        if (title is not None and stat is not None)
        else None
    )
    if t is None:
        failures.append(Unpriced.TITLE_UNPARSED)
    else:
        player_name = t["name"]
        if x is not None and int(t["x"]) != x:
            failures.append(Unpriced.X_MISMATCH)

    custom = market.get("custom_strike")
    custom = custom if isinstance(custom, Mapping) else {}
    player_uuid = _str(custom.get("football_player"))
    if player_uuid is None:
        failures.append(Unpriced.PLAYER_UUID_MISSING)

    team_code = _team_code(m["teams"], m["player"], team_codes) if m is not None else None
    if team_code is None:
        failures.append(Unpriced.TEAM_CODE_UNPARSED)

    order = list(Unpriced)
    reason = min(failures, key=order.index) if failures else None
    return ScopedMarket(
        ticker=ticker,
        event_ticker=event_ticker,
        series=series,
        x=x,
        floor_strike=floor_strike,
        strike_type=strike_type,
        cap_strike=cap_strike,
        player_uuid=player_uuid,
        team_uuid=_str(custom.get("football_team")),
        player_name=player_name,
        team_code=team_code,
        priced=reason is None,
        reason=reason,
    )
