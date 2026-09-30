"""DATA-08 Kalshi history for one NFL week, fetched event by event (approved 2026-09-30).

For every approved series: list its events (GET /events keeps every event, even once its
markets are archived), keep those whose ticker date is one of the week's game dates, and for
each event fetch its markets from the live and historical endpoints, then their trades and
hourly candles. Each event is written as soon as it finishes, market rows last, so a slow run
shows progress and a rerun skips events already stored."""

from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import polars as pl

from ge.ingest.kalshi import KalshiPublic, event_ticker_date, events_on_dates, markets_for_event
from ge.ingest.prices import book_asks, dollars_to_cc
from ge.ingest.raw import DATA_ROOT, partitions, write_raw
from ge.store.known_at import kalshi_ingest_week

GAME_WINNER_SERIES = "KXNFLGAME"  # the game row of the EDG-02 fee table (config/fees.yaml)
KALSHI_DATASETS = ("kalshi_markets", "kalshi_orderbook", "kalshi_candles", "kalshi_trades")
_TS = "%Y%m%dT%H%M%SZ"


@dataclass
class HistoryResult:
    events_by_series: dict[str, int] = field(default_factory=dict)
    skipped_events: int = 0
    markets_by_series: dict[str, int] = field(default_factory=dict)


def _ts(raw: str) -> dt.datetime:
    return dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _occurs(m: dict[str, Any]) -> dt.datetime | None:
    raw = m.get("occurrence_datetime") or m.get("expected_expiration_time")
    return _ts(raw) if raw else None


def week_game_dates(sched: pl.DataFrame, week: int) -> set[dt.date]:
    """DATA-08: the (Eastern) game dates of a schedule week."""
    return {dt.date.fromisoformat(d) for d in sched.filter(pl.col("week") == week)["gameday"]}


def market_row(
    m: dict[str, Any], series: str, week: int, historical: bool,
    yes_ask: int | None = None, no_ask: int | None = None,
) -> dict[str, Any]:  # fmt: skip
    """DATA-08: one stored kalshi_markets row."""
    return {
        "ticker": m["ticker"],
        "event_ticker": m.get("event_ticker"),
        "series_ticker": series,
        "status": m.get("status"),
        "yes_sub_title": m.get("yes_sub_title"),
        "occurs_at": _occurs(m),
        "close_time": m.get("close_time"),
        "yes_ask_cc": yes_ask,
        "no_ask_cc": no_ask,
        "volume_fp": m.get("volume_fp"),
        "rules_primary": m.get("rules_primary"),
        "rules_secondary": m.get("rules_secondary"),
        "raw_json": json.dumps(m),
        "nfl_week": week,
        "historical": historical,
    }


def _stored(root: Path, dataset: str, season: int) -> pl.DataFrame:
    parts = [pl.read_parquet(p / "part.parquet") for p in partitions(root, dataset, season)]
    return pl.concat(parts, how="diagonal_relaxed") if parts else pl.DataFrame()


def completed_events(root: Path, season: int, week: int) -> set[str]:
    """DATA-08: events whose market rows are stored for this week (written last per event)."""
    df = _stored(root, "kalshi_markets", season)
    if df.is_empty() or "event_ticker" not in df.columns:
        return set()
    return set(df.filter(kalshi_ingest_week(df) == week)["event_ticker"].drop_nulls().to_list())


def market_counts(root: Path, season: int, week: int) -> dict[str, int]:
    """DATA-08: distinct stored markets per series for this week."""
    df = _stored(root, "kalshi_markets", season)
    if df.is_empty():
        return {}
    wk = df.filter(kalshi_ingest_week(df) == week)
    return dict(sorted(Counter(wk.unique("ticker")["series_ticker"].to_list()).items()))


def unique_pulled_at(root: Path, season: int, now: dt.datetime) -> dt.datetime:
    """A pull time (whole seconds, UTC) later than every stored Kalshi partition this season,
    so per-event writes never collide on a partition directory."""
    t = now.astimezone(dt.UTC).replace(microsecond=0)
    for ds in KALSHI_DATASETS:
        for p in partitions(root, ds, season):
            last = dt.datetime.strptime(p.name.split("=", 1)[1], _TS).replace(tzinfo=dt.UTC)
            t = max(t, last + dt.timedelta(seconds=1))
    return t


def game_winner_coverage(
    sched: pl.DataFrame, week: int, event_tickers: list[str]
) -> list[dict[str, Any]]:
    """DATA-08: per game date, scheduled games vs KXNFLGAME events found. Counts only: Kalshi
    team codes are not mapped to nflverse's here (that is Phase 6)."""
    games = Counter(
        dt.date.fromisoformat(d) for d in sched.filter(pl.col("week") == week)["gameday"]
    )
    events = Counter(
        event_ticker_date(t) for t in event_tickers if t.startswith(f"{GAME_WINNER_SERIES}-")
    )
    return [
        {"date": d, "games": n, "events": events.get(d, 0), "ok": events.get(d, 0) == n}
        for d, n in sorted(games.items())
    ]


def _write(
    rows: list[dict[str, Any]], dataset: str, season: int, source: str, root: Path,
    now: Callable[[], dt.datetime],
) -> None:  # fmt: skip
    if rows:
        write_raw(
            pl.DataFrame(rows, infer_schema_length=None),
            dataset,
            season,
            source=source,
            root=root,
            pulled_at=unique_pulled_at(root, season, now()),
        )


def run_history(
    k: KalshiPublic,
    *,
    season: int,
    week: int,
    sched: pl.DataFrame,
    series: list[str],
    root: Path = DATA_ROOT,
    log: Callable[[str], None] = print,
    now: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC),
) -> HistoryResult:
    """DATA-08: pull markets, trades and hourly candles for every event of the week."""
    dates = week_game_dates(sched, week)
    done = completed_events(root, season, week)
    result = HistoryResult()
    log(f"{season} week {week}: game dates {sorted(d.isoformat() for d in dates)}; "
        f"{len(series)} series; {len(done)} events already stored")  # fmt: skip
    for i, s in enumerate(series, 1):
        evs = events_on_dates(list(k.events(series_ticker=s)), dates)
        result.events_by_series[s] = len(evs)
        log(f"[{i}/{len(series)}] {s}: {len(evs)} events on the week's dates")
        for e in evs:
            et = e["event_ticker"]
            if et in done:
                result.skipped_events += 1
                continue
            source = f"Kalshi public API (DATA-08) {et} week {week}"
            markets, books, trades, candles = [], [], [], []
            for m, hist in markets_for_event(k, et):
                yes_ask = no_ask = None
                if not hist:
                    book = k.orderbook(m["ticker"])
                    yes_ask, no_ask = book_asks(book)
                    for side in ("yes", "no"):
                        for price, qty in book.get(f"{side}_dollars") or []:
                            books.append({"ticker": m["ticker"], "side": side,
                                          "bid_cc": dollars_to_cc(price), "qty": qty,
                                          "nfl_week": week})  # fmt: skip
                opened = int(_ts(m["open_time"]).timestamp())
                if hist:
                    tr = k.historical_trades(m["ticker"])
                    cs = k.historical_candlesticks(
                        m["ticker"], opened, int(_ts(m["close_time"]).timestamp())
                    )
                else:
                    tr = k.trades(m["ticker"])
                    cs = k.candlesticks(s, m["ticker"], opened, int(now().timestamp()))
                trades += [{**t, "ticker": m["ticker"], "nfl_week": week} for t in tr]
                candles += [
                    {"ticker": m["ticker"], "raw_json": json.dumps(c),
                     "end_period_ts": c.get("end_period_ts"), "nfl_week": week}
                    for c in cs
                ]  # fmt: skip
                markets.append(market_row(m, s, week, hist, yes_ask, no_ask))
            _write(candles, "kalshi_candles", season, source, root, now)
            _write(trades, "kalshi_trades", season, source, root, now)
            _write(books, "kalshi_orderbook", season, source, root, now)
            _write(markets, "kalshi_markets", season, source, root, now)  # last: marks done
            log(f"    {et}: {len(markets)} markets, {len(trades)} trades, {len(candles)} candles")
    result.markets_by_series = market_counts(root, season, week)
    return result
