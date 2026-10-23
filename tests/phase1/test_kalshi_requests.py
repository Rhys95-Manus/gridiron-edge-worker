"""DATA-08: Kalshi request budget for the scheduled pull (user ruling 2026-10-20).

(a) a client-side rate limiter at Kalshi's documented read rate, (b) order books only for the
series we intend to price and only inside the decision window before kickoff, every other
market taking its asks from the /markets record, (c) the 429 count and timestamped progress
reported for each run.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from itertools import pairwise
from typing import Any

import httpx
import polars as pl
import pytest

from ge.config import load_ingest, load_params
from ge.ingest import collect
from ge.ingest.http import PublicClient, RateLimiter
from ge.ingest.jobs import (
    KalshiRunStats,
    collect_week_markets,
    kalshi_rate_per_second,
    kickoffs_by_date,
    orderbook_lead,
    wants_orderbook,
)
from ge.ingest.prices import book_asks, market_asks
from ge.store.known_at import week_window
from tests.phase1.conftest import load_fixture
from tests.phase2.conftest import load_parquet_fixture

CFG = load_ingest()
KALSHI = CFG.kalshi
RATE_DOC = "https://docs.kalshi.com/getting_started/rate_limits"


# --- (a) rate limiter -------------------------------------------------------------------------


class FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0
        self.slept: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.slept.append(s)
        self.t += s


def test_rate_comes_from_kalshis_documented_read_budget() -> None:
    assert RATE_DOC in KALSHI.read_tokens_per_second.source
    assert RATE_DOC in KALSHI.tokens_per_request.source
    assert kalshi_rate_per_second(KALSHI) == (
        KALSHI.read_tokens_per_second.value / KALSHI.tokens_per_request.value
    )


def test_limiter_spaces_requests_at_least_one_interval_apart() -> None:
    clock = FakeClock()
    lim = RateLimiter(20.0, clock=clock.now, sleep=clock.sleep)
    starts = []
    for _ in range(50):
        lim.wait()
        starts.append(clock.t)
    gaps = [b - a for a, b in pairwise(starts)]
    assert min(gaps) >= 1 / 20 - 1e-12
    assert len(clock.slept) == 49  # the first call never waits
    assert starts[-1] - starts[0] == pytest.approx(49 / 20)


def test_limiter_does_not_wait_when_the_caller_is_already_slower() -> None:
    clock = FakeClock()
    lim = RateLimiter(20.0, clock=clock.now, sleep=clock.sleep)
    lim.wait()
    clock.t += 1.0
    lim.wait()
    assert clock.slept == []


def _client(handler: Any, limiter: RateLimiter | None) -> PublicClient:
    http = CFG.http.model_copy(
        update={
            "backoff_initial_seconds": CFG.http.backoff_initial_seconds.model_copy(
                update={"value": 0}
            ),
            "backoff_max_seconds": CFG.http.backoff_max_seconds.model_copy(update={"value": 0}),
        }
    )
    c = PublicClient(http, rate_limiter=limiter)
    c._client = httpx.Client(transport=httpx.MockTransport(handler))
    return c


def test_client_counts_every_attempt_and_every_429_and_limits_each_attempt() -> None:
    replies = iter([429, 429, 200, 200])
    clock = FakeClock()
    waits: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        waits.append(clock.t)
        return httpx.Response(next(replies), json={})

    c = _client(handler, RateLimiter(20.0, clock=clock.now, sleep=clock.sleep))
    c.get_json("https://example.test/a")
    c.get_json("https://example.test/b")
    assert c.attempts == 4
    assert c.retryable_by_status == {429: 2}
    assert [round(b - a, 9) for a, b in pairwise(waits)] == [0.05] * 3


# --- (b) asks without an order book ------------------------------------------------------------


def test_market_record_asks_match_the_order_book_asks() -> None:
    fx = load_fixture("kalshi_orderbook.json")
    assert market_asks(fx["market"]) == book_asks(fx["response"]["orderbook_fp"])


def test_market_with_nothing_resting_has_no_asks() -> None:
    empty = {
        "yes_ask_dollars": "1.0000",
        "yes_ask_size_fp": "0.00",
        "no_ask_dollars": "1.0000",
        "yes_bid_dollars": "0.0000",
        "yes_bid_size_fp": "0.00",
    }
    assert market_asks(empty) == (None, None) == book_asks({})


# --- (b) which markets get an order book --------------------------------------------------------

SEASON = 2025


def _sched() -> pl.DataFrame:
    return load_parquet_fixture("schedules_2023_2026").filter(pl.col("season") == SEASON)


def test_price_set_is_the_user_ruling_of_2026_10_20() -> None:
    s = KALSHI.orderbook_series
    assert "2026-10-20" in s.source
    assert set(s.value) == {
        "KXNFLPASSYDS",
        "KXNFLRECYDS",
        "KXNFLRSHYDS",
        "KXNFLREC",
        "KXNFLTD",
        "KXNFLFIRSTTD",
        "KXNFLGAME",
        "KXNFLSPREAD",
        "KXNFLTOTAL",
    }


def test_lead_is_bt01_first_decision_time_plus_the_longest_collector_gap() -> None:
    hours = load_params().backtest.bt_01_decision_hours_before_kickoff.value
    gap = KALSHI.orderbook_collector_gap_hours.value
    assert orderbook_lead(KALSHI) == dt.timedelta(hours=hours + gap)


def _game(sched: pl.DataFrame, week: int) -> dict[str, Any]:
    return sched.filter(pl.col("week") == week).sort(["gameday", "gametime"]).row(0, named=True)


def _ticker(series: str, day: dt.date, tail: str = "X") -> dict[str, Any]:
    tag = day.strftime("%y%b%d").upper()
    return {"ticker": f"{series}-{tag}{tail}-1", "event_ticker": f"{series}-{tag}{tail}"}


def test_order_book_only_inside_the_window_and_only_for_price_set_series() -> None:
    sched = _sched()
    kick = kickoffs_by_date(sched)
    g = _game(sched, 6)
    day = dt.date.fromisoformat(g["gameday"])
    first = min(kick[day])
    last = max(kick[day])
    lead = orderbook_lead(KALSHI)
    book = set(KALSHI.orderbook_series.value)
    m = _ticker("KXNFLRECYDS", day)

    assert not wants_orderbook(m, book, kick, first - lead - dt.timedelta(seconds=1), lead)
    assert wants_orderbook(m, book, kick, first - lead, lead)
    assert wants_orderbook(m, book, kick, last - dt.timedelta(seconds=1), lead)
    assert not wants_orderbook(m, book, kick, last, lead)  # in play: no pregame book
    # same time, a series outside the price set
    assert not wants_orderbook(_ticker("KXNFLRECYDSPROT", day), book, kick, first - lead, lead)
    # a date with no game, and a ticker with no date
    assert not wants_orderbook(
        _ticker("KXNFLRECYDS", day + dt.timedelta(days=1)),
        book,
        kick,
        first - lead,
        lead,
    )
    assert not wants_orderbook(
        {"ticker": "KXNFLGAME-SEASON-1", "event_ticker": "KXNFLGAME-SEASON"},
        book,
        kick,
        first,
        lead,
    )


class FakeKalshi:
    def __init__(self, markets: dict[str, list[dict[str, Any]]], book: dict[str, Any]) -> None:
        self._markets = markets
        self._book = book
        self.book_calls: list[str] = []

    def markets(self, **filters: Any) -> Iterator[dict[str, Any]]:
        return iter(self._markets.get(filters["series_ticker"], []))

    def orderbook(self, ticker: str) -> dict[str, Any]:
        self.book_calls.append(ticker)
        return self._book


def test_week_pull_books_only_qualifying_markets_and_reports_progress() -> None:
    fx = load_fixture("kalshi_orderbook.json")
    sched = _sched()
    kick = kickoffs_by_date(sched)
    start, end = week_window(sched, 6)
    g = _game(sched, 6)
    day = dt.date.fromisoformat(g["gameday"])
    now = min(kick[day]) - dt.timedelta(hours=2)
    occurs = (max(kick[day]) + dt.timedelta(hours=1)).isoformat()

    def mk(series: str, n: int) -> dict[str, Any]:
        base = _ticker(series, day, tail=f"G{n}")
        return {**fx["market"], **base, "occurrence_datetime": occurs}

    markets = {
        "KXNFLRECYDS": [mk("KXNFLRECYDS", 1), mk("KXNFLRECYDS", 2)],
        "KXNFLRECYDSPROT": [mk("KXNFLRECYDSPROT", 3)],
    }
    k = FakeKalshi(markets, fx["response"]["orderbook_fp"])
    lines: list[str] = []
    stats = KalshiRunStats()
    market_rows, book_rows = collect_week_markets(
        k,
        ["KXNFLRECYDS", "KXNFLRECYDSPROT"],
        week=6,
        start=start,
        end=end,
        now=now,
        kickoffs=kick,
        book_series=set(KALSHI.orderbook_series.value),
        lead=orderbook_lead(KALSHI),
        progress=lines.append,
        stats=stats,
    )
    assert k.book_calls == [m["ticker"] for m in markets["KXNFLRECYDS"]]
    assert stats.markets == 3 and stats.orderbooks == 2
    by = {r["ticker"]: r for r in market_rows}
    want = book_asks(fx["response"]["orderbook_fp"])
    for m in markets["KXNFLRECYDS"]:
        assert (by[m["ticker"]]["yes_ask_cc"], by[m["ticker"]]["no_ask_cc"]) == want
        assert by[m["ticker"]]["ask_source"] == "orderbook"
    prot = by[markets["KXNFLRECYDSPROT"][0]["ticker"]]
    assert (prot["yes_ask_cc"], prot["no_ask_cc"]) == market_asks(fx["market"])
    assert prot["ask_source"] == "market"
    assert {r["ticker"] for r in book_rows} == {m["ticker"] for m in markets["KXNFLRECYDS"]}
    assert lines and all(dt.datetime.fromisoformat(ln.split()[0]).tzinfo for ln in lines)


def test_next_weeks_priced_markets_inside_the_window_are_pulled_too() -> None:
    """Thursday gap (ruling 2026-10-23): a week starts at 00:00 ET on its first game date, so
    a Thursday game's -24 h decision time falls in the previous week. Next week's priced
    markets inside the order-book window are pulled (with their book) and stored under next
    week; its other markets wait for their own week."""
    fx = load_fixture("kalshi_orderbook.json")
    sched = _sched()
    kick = kickoffs_by_date(sched)
    lead = orderbook_lead(KALSHI)
    start6, end6 = week_window(sched, 6)
    start7, end7 = week_window(sched, 7)
    g7 = _game(sched, 7)
    day7 = dt.date.fromisoformat(g7["gameday"])
    first7 = min(kick[day7])
    now = first7 - dt.timedelta(hours=30)  # the -24 h decision time is still ahead
    assert end6 is not None and start6 <= now < end6  # still inside week 6
    assert now >= first7 - lead
    later7 = sorted(
        {dt.date.fromisoformat(d) for d in sched.filter(pl.col("week") == 7)["gameday"]}
    )
    far_day = later7[-1]  # the week's last game date, outside the window at `now`
    assert all(k - lead > now for k in kick[far_day])
    occurs7 = (max(kick[day7]) + dt.timedelta(hours=1)).isoformat()
    occurs_far = (max(kick[far_day]) + dt.timedelta(hours=1)).isoformat()

    def mk(series: str, day: dt.date, n: int, occurs: str) -> dict[str, Any]:
        return {**fx["market"], **_ticker(series, day, tail=f"N{n}"), "occurrence_datetime": occurs}

    near_priced = mk("KXNFLRECYDS", day7, 1, occurs7)
    near_unpriced = mk("KXNFLRECYDSPROT", day7, 2, occurs7)
    far_priced = mk("KXNFLRECYDS", far_day, 3, occurs_far)
    markets = {
        "KXNFLRECYDS": [near_priced, far_priced],
        "KXNFLRECYDSPROT": [near_unpriced],
    }
    k = FakeKalshi(markets, fx["response"]["orderbook_fp"])
    stats = KalshiRunStats()
    market_rows, book_rows = collect_week_markets(
        k,
        ["KXNFLRECYDS", "KXNFLRECYDSPROT"],
        week=6,
        start=start6,
        end=end6,
        now=now,
        kickoffs=kick,
        book_series=set(KALSHI.orderbook_series.value),
        lead=lead,
        progress=lambda s: None,
        stats=stats,
        next_week=(7, start7, end7),
    )
    assert [r["ticker"] for r in market_rows] == [near_priced["ticker"]]
    assert market_rows[0]["nfl_week"] == 7 and market_rows[0]["ask_source"] == "orderbook"
    assert k.book_calls == [near_priced["ticker"]]
    assert {r["nfl_week"] for r in book_rows} == {7}
    assert stats.next_week_markets == 1


def test_run_summary_carries_requests_and_429s() -> None:
    s = KalshiRunStats(requests=120, http_429=3, markets=900, orderbooks=40, seconds=12.5)
    text = s.summary()
    assert "requests 120" in text and "HTTP 429 x3" in text and "order books 40" in text


def test_collect_step_detail_reports_the_request_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    sched = _sched()
    start, _ = week_window(sched, 5)

    def fake_run_kalshi(
        cfg: Any, season: int, week: int, history: bool, stats: KalshiRunStats | None = None
    ) -> int:
        assert stats is not None
        stats.requests, stats.http_429, stats.orderbooks = 77, 2, 10
        return 0

    monkeypatch.setattr(collect, "current_season", lambda: SEASON)
    monkeypatch.setattr(collect, "_schedules", lambda seasons: sched)
    monkeypatch.setattr(collect, "_now", lambda: start + dt.timedelta(hours=30))
    monkeypatch.setattr(collect, "run_kalshi", fake_run_kalshi)
    ok, detail = collect.default_steps()[0].run()
    assert ok
    assert "requests 77" in detail and "HTTP 429 x2" in detail
