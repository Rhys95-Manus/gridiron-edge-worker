"""SHD-01 / SHD-04 / SHD-19: one game's snapshot of the three PRV-01 series.

SHD-01: "Every market in the three series for that game is logged, priced or not."
SHD-19: "Snapshots taken before pricer v0 is frozen are logged with every market unpriced
(reason pricer_not_frozen)."
Each market gets its PRV-01 scope result, its PRV-02 map result (one lookup per player and
team) and its order book from the order-book endpoint (SHD-10). Markets come from GET /markets
per series with min_close_ts = kickoff; an event belongs to the game when PRV-02's event match
(same date, same two teams) picks this game. PRV-02: an event with no matching schedules game
is a data gap and is left out; a Kalshi team code missing from the config stops the run.

Live GET /markets records carry no series_ticker (first live tick, 2026-11-21), so each market
takes the series_ticker its request named, as the Phase-4 collector stores it; a record that
does carry one keeps its own. market_json stays the record as received."""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from ge.config import load_params
from ge.ingest.prices import dollars_to_cc
from ge.pricer_v0.scope import PRV01_SERIES, scope_market
from ge.pricer_v0.teams import GameNotMatched, ScheduleGame, game_of_event, parse_prop_event
from ge.shadow.book import book_summary
from ge.shadow.schedule import PRICING_MODE_CAPTURE, GameKick, Window

# SHD-19: "logged with every market unpriced (reason pricer_not_frozen)".
PRICER_NOT_FROZEN = "pricer_not_frozen"


class MarketSource(Protocol):
    def markets(self, **filters: Any) -> Iterator[dict[str, Any]]: ...

    def orderbook(self, ticker: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class MapResult:
    """PRV-02 verdict as logged: mapped, or the unmapped/data-gap reason."""

    mapped: bool
    reason: str | None
    gsis_id: str | None
    nflverse_team: str | None
    roster_week: int | None
    roster_pulled_at: dt.datetime | None


Mapper = Callable[[str, str, int], MapResult]


@dataclass
class Snapshot:
    """One game's capture: market rows, order-book level rows, and the outcome (ok or
    no_markets)."""

    outcome: str
    rows: list[dict[str, Any]] = field(default_factory=list)
    book_rows: list[dict[str, Any]] = field(default_factory=list)
    n_markets: int = 0
    n_books: int = 0


def _cc(value: Any) -> int | None:
    return None if value in (None, "") else dollars_to_cc(str(value))


def _fp(value: Any) -> float | None:
    return None if value in (None, "") else float(str(value))


def game_markets(
    k: MarketSource,
    game: GameKick,
    games: Iterable[ScheduleGame],
    team_codes: frozenset[str],
    team_map: Mapping[str, str],
) -> list[tuple[str, dict[str, Any]]]:
    """SHD-01: every market of the three series whose event is this game (PRV-02 match),
    with the series_ticker its request named."""
    games = list(games)
    verdict: dict[str, bool] = {}
    out: list[tuple[str, dict[str, Any]]] = []
    for series in PRV01_SERIES:
        for m in k.markets(series_ticker=series, min_close_ts=int(game.kickoff_utc.timestamp())):
            ev = str(m["event_ticker"])
            if ev not in verdict:
                kg = parse_prop_event(ev, team_codes)  # TeamMapError: config error, stops
                try:
                    verdict[ev] = game_of_event(kg, team_map, games).game_id == game.game_id
                except GameNotMatched:
                    verdict[ev] = False  # PRV-02 data gap: not attributable to this game
            if verdict[ev]:
                out.append((series, m))
    return out


def take_snapshot(
    k: MarketSource,
    game: GameKick,
    window: Window,
    *,
    games: Iterable[ScheduleGame],
    team_codes: frozenset[str],
    team_map: Mapping[str, str],
    mapper: Mapper,
    clock: Callable[[], dt.datetime],
    code_commit: str | None,
) -> Snapshot:
    """SHD-01: snapshot one game for one window. taken_ts is when the snapshot starts; each
    row also records when its order book was read (book_ts)."""
    taken = clock()
    markets = game_markets(k, game, games, team_codes, team_map)
    if not markets:
        return Snapshot("no_markets")
    window_cc = int(load_params().edge.edg_04_depth_window_cc.value)
    key = {
        "game_id": game.game_id,
        "season": game.season,
        "week": game.week,
        "kickoff_utc": game.kickoff_utc,
        "snapshot_type": str(window.snapshot_type),
        "target_ts": window.target,
        "taken_ts": taken,
    }
    maps: dict[tuple[str, str], MapResult] = {}
    snap = Snapshot("ok")
    for requested, m in sorted(markets, key=lambda x: str(x[1]["ticker"])):
        series = m.get("series_ticker") or requested
        sm = scope_market({**m, "series_ticker": series}, team_codes)
        mr: MapResult | None = None
        if sm.priced and sm.player_name is not None and sm.team_code is not None:
            mk = (sm.player_name, sm.team_code)
            if mk not in maps:
                maps[mk] = mapper(sm.player_name, sm.team_code, game.week)
            mr = maps[mk]
        book = k.orderbook(str(m["ticker"]))
        book_ts = clock()
        snap.n_books += 1
        b = book_summary(book, window_cc)
        for side in ("yes", "no"):
            for price, qty in book.get(f"{side}_dollars") or []:
                snap.book_rows.append(
                    {
                        **key,
                        "ticker": m["ticker"],
                        "side": side,
                        "bid_cc": dollars_to_cc(price),
                        "qty": str(qty),
                        "book_ts": book_ts,
                        "pricing_mode": PRICING_MODE_CAPTURE,
                    }
                )
        snap.rows.append(
            {
                **key,
                "lateness_s": (taken - window.target).total_seconds(),
                "book_ts": book_ts,
                "series": series,
                "event_ticker": m.get("event_ticker"),
                "ticker": m["ticker"],
                "market_status": m.get("status"),
                "floor_strike": sm.floor_strike,
                "strike_type": sm.strike_type,
                "x": sm.x,
                "prv01_in_scope": sm.priced,
                "prv01_reason": None if sm.reason is None else str(sm.reason),
                "kalshi_player_uuid": sm.player_uuid,
                "team_code": sm.team_code,
                "prv02_mapped": None if mr is None else mr.mapped,
                "prv02_reason": None if mr is None else mr.reason,
                "gsis_id": None if mr is None else mr.gsis_id,
                "nflverse_team": None if mr is None else mr.nflverse_team,
                "roster_week": None if mr is None else mr.roster_week,
                "roster_pulled_at": None if mr is None else mr.roster_pulled_at,
                "yes_bid_cc": b.yes_bid_cc,
                "yes_bid_size": b.yes_bid_size,
                "no_bid_cc": b.no_bid_cc,
                "no_bid_size": b.no_bid_size,
                "yes_ask_cc": b.yes_ask_cc,
                "yes_ask_size": b.yes_ask_size,
                "no_ask_cc": b.no_ask_cc,
                "no_ask_size": b.no_ask_size,
                "spread_cc": b.spread_cc,
                "yes_bid_depth_2c": b.yes_bid_depth,
                "no_bid_depth_2c": b.no_bid_depth,
                "last_price_cc": _cc(m.get("last_price_dollars")),
                "volume_fp": _fp(m.get("volume_fp")),
                "volume_24h_fp": _fp(m.get("volume_24h_fp")),
                "open_interest_fp": _fp(m.get("open_interest_fp")),
                "priced": False,
                "p_yes": None,
                "action": None,
                "unpriced_reason": PRICER_NOT_FROZEN,
                "pricing_mode": PRICING_MODE_CAPTURE,
                "code_commit": code_commit,
                "market_json": json.dumps(m, sort_keys=True, ensure_ascii=False),
            }
        )
    snap.n_markets = len(snap.rows)
    return snap
