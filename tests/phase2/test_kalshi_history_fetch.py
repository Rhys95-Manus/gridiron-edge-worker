"""DATA-08 history by event (approved 2026-09-30): list each series' events (GET /events),
keep those whose ticker date is a game date of the week, fetch each event's markets from the
live and historical market endpoints (event_ticker filter), and write every event as it
finishes so a slow run shows progress and can resume. Fixtures are real Kalshi responses."""

from __future__ import annotations

import datetime as dt
import functools
from pathlib import Path
from typing import Any

import polars as pl
import pytest

from ge.ingest.kalshi import event_ticker_date, events_on_dates, markets_for_event
from ge.ingest.kalshi_history import (
    completed_events,
    game_winner_coverage,
    run_history,
    unique_pulled_at,
    week_game_dates,
)
from ge.ingest.raw import partitions, write_raw
from tests.phase2.conftest import load_json_fixture, load_parquet_fixture


@functools.cache
def _events() -> Any:
    return load_json_fixture("kalshi_events_kxnflgame.json")["response"]["events"]


@functools.cache
def _event_markets() -> Any:
    return load_json_fixture("kalshi_event_markets.json")


@functools.cache
def _candles() -> Any:
    return load_json_fixture("kalshi_candles_2025w10.json")


def _sched_2025() -> pl.DataFrame:
    return load_parquet_fixture("schedules_2023_2026").filter(pl.col("season") == 2025)


def test_event_ticker_date_parses_every_game_event() -> None:
    dates = [event_ticker_date(e["event_ticker"]) for e in _events()]
    assert all(d is not None for d in dates), [
        e["event_ticker"] for e, d in zip(_events(), dates, strict=True) if d is None
    ]
    assert event_ticker_date(_event_markets()["archived_event"]) == dt.date.fromisoformat(
        _sched_2025().filter(pl.col("week") == 10).sort("gameday")["gameday"][-1]
    )
    assert event_ticker_date("KXNFLMVP-26") is None
    assert event_ticker_date("KXNFLGAME-25FOO09PITLAC") is None


def test_week_events_match_the_week_game_count_per_date() -> None:
    sched = _sched_2025()
    dates = week_game_dates(sched, 10)
    picked = events_on_dates(_events(), dates)
    assert {event_ticker_date(e["event_ticker"]) for e in picked} <= dates
    cov = game_winner_coverage(sched, 10, [e["event_ticker"] for e in picked])
    assert cov and all(r["ok"] for r in cov), cov
    assert sum(r["events"] for r in cov) == sched.filter(pl.col("week") == 10).height


def test_coverage_flags_a_missing_game_event() -> None:
    sched = _sched_2025()
    picked = [e["event_ticker"] for e in events_on_dates(_events(), week_game_dates(sched, 10))]
    cov = game_winner_coverage(sched, 10, picked[1:])
    bad = [r for r in cov if not r["ok"]]
    assert len(bad) == 1 and bad[0]["events"] == bad[0]["games"] - 1


class FakeKalshi:
    """Serves the captured real responses; records calls; can fail on one ticker."""

    def __init__(self, fail_on: str | None = None) -> None:
        self.fail_on = fail_on
        self.calls: list[str] = []
        self.candles = {
            m["market"]["ticker"]: m["response"]["candlesticks"] for m in _candles()["markets"]
        }

    def events(self, **filters: Any) -> list[dict[str, Any]]:
        self.calls.append(f"events {filters.get('series_ticker')}")
        return [e for e in _events() if e["series_ticker"] == filters.get("series_ticker")]

    def markets(self, **filters: Any) -> list[dict[str, Any]]:
        self.calls.append(f"markets {filters.get('event_ticker')}")
        r = _event_markets()["response"].get(filters.get("event_ticker"), {})
        return list(r.get("live", []))

    def historical_markets(self, **filters: Any) -> list[dict[str, Any]]:
        self.calls.append(f"historical_markets {filters.get('event_ticker')}")
        r = _event_markets()["response"].get(filters.get("event_ticker"), {})
        return list(r.get("historical", []))

    def orderbook(self, ticker: str) -> dict[str, Any]:
        return {}

    def trades(self, ticker: str, **_: Any) -> list[dict[str, Any]]:
        return []

    def historical_trades(self, ticker: str, **_: Any) -> list[dict[str, Any]]:
        return []

    def candlesticks(self, series: str, ticker: str, a: int, b: int) -> list[dict[str, Any]]:
        return self.historical_candlesticks(ticker, a, b)

    def historical_candlesticks(self, ticker: str, a: int, b: int) -> list[dict[str, Any]]:
        self.calls.append(f"candles {ticker}")
        if ticker == self.fail_on:
            raise RuntimeError("simulated failure")
        return self.candles.get(ticker, [])


def test_markets_for_event_uses_both_endpoints_live_wins() -> None:
    k = FakeKalshi()
    old = markets_for_event(k, _event_markets()["archived_event"])  # type: ignore[arg-type]
    assert old and all(hist for _, hist in old)
    live = markets_for_event(k, _event_markets()["live_event"])  # type: ignore[arg-type]
    assert live and not any(hist for _, hist in live)
    k2 = FakeKalshi()
    ev = _event_markets()["archived_event"]
    both = _event_markets()["response"][ev]["historical"]
    k2.markets = lambda **f: list(both)  # type: ignore[method-assign]
    got = markets_for_event(k2, ev)  # type: ignore[arg-type]
    assert len(got) == len(both) and not any(hist for _, hist in got)


def _run(root: Path, k: FakeKalshi, log: list[str]) -> Any:
    ev = _event_markets()["archived_event"]
    only = [e for e in _events() if e["event_ticker"] == ev]
    k.events = lambda **f: list(only)  # type: ignore[method-assign]
    return run_history(
        k,  # type: ignore[arg-type]
        season=2025,
        week=10,
        sched=_sched_2025(),
        series=["KXNFLGAME"],
        root=root,
        log=log.append,
    )


def test_each_event_is_written_when_done_and_a_rerun_resumes(tmp_path: Path) -> None:
    ev = _event_markets()["archived_event"]
    tickers = [m["ticker"] for m in _event_markets()["response"][ev]["historical"]]
    log: list[str] = []
    with pytest.raises(RuntimeError, match="simulated"):
        _run(tmp_path, FakeKalshi(fail_on=tickers[-1]), log)
    assert completed_events(tmp_path, 2025, 10) == set()  # market rows are written last
    ok = FakeKalshi()
    result = _run(tmp_path, ok, log)
    assert completed_events(tmp_path, 2025, 10) == {ev}
    assert result.markets_by_series == {"KXNFLGAME": len(tickers)}
    assert any(ev in line for line in log), log
    again = FakeKalshi()
    _run(tmp_path, again, log)
    assert not any(c.startswith("candles") for c in again.calls), "finished event re-fetched"
    stored = pl.concat(
        [pl.read_parquet(p / "part.parquet") for p in partitions(tmp_path, "kalshi_candles", 2025)]
    )
    assert set(stored["ticker"].to_list()) == set(tickers)
    assert (stored["nfl_week"] == 10).all()


def test_unique_pulled_at_never_reuses_a_partition_second(tmp_path: Path) -> None:
    t = dt.datetime(2026, 9, 30, 12, 0, 0, tzinfo=dt.UTC)
    df = pl.DataFrame({"ticker": ["A"], "nfl_week": [10]})
    write_raw(df, "kalshi_markets", 2025, source="t", root=tmp_path, pulled_at=t)
    nxt = unique_pulled_at(tmp_path, 2025, t)
    assert nxt > t
    assert write_raw(df.with_columns(pl.lit("B").alias("ticker")), "kalshi_markets", 2025,
                     source="t", root=tmp_path, pulled_at=nxt)  # fmt: skip
    assert len(partitions(tmp_path, "kalshi_markets", 2025)) == 2
