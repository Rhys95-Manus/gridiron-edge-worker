"""DATA-08: adaptive Kalshi rate limit (user ruling 2026-10-22).

Kalshi's unauthenticated limit is below the documented Basic budget (65 x 429 at 20/s on the
2026-10-20 run). On a 429 the limiter halves its rate, never below the floor in ingest.yaml;
after a quiet period with no 429 it steps back up, never above the documented rate. Tested
against a fake server that answers 429 whenever more than its threshold of requests arrived
in the last second.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Any

import httpx

from ge.config import load_ingest
from ge.ingest.http import AdaptiveRateLimiter, PublicClient
from ge.ingest.jobs import KalshiRunStats, kalshi_limiter, kalshi_rate_per_second

CFG = load_ingest()
KALSHI = CFG.kalshi
MAX = kalshi_rate_per_second(KALSHI)
FLOOR = float(KALSHI.min_requests_per_second.value)
QUIET = float(KALSHI.rate_recovery_quiet_seconds.value)
STEP = float(KALSHI.rate_recovery_step_per_second.value)


class FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def now(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.t += s


class FakeServer:
    """429 when more than `threshold` requests arrived in the last second (inclusive of this
    one); otherwise 200. Uses the shared fake clock, and each request takes `latency` s."""

    def __init__(self, clock: FakeClock, threshold: int, latency: float = 0.0) -> None:
        self.clock = clock
        self.threshold = threshold
        self.latency = latency
        self.seen: deque[float] = deque()
        self.n_429 = 0
        self.n_ok = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        now = self.clock.t
        while self.seen and self.seen[0] <= now - 1.0:
            self.seen.popleft()
        self.seen.append(now)
        self.clock.t += self.latency
        if len(self.seen) > self.threshold:
            self.n_429 += 1
            return httpx.Response(429, json={"error": "too many requests"})
        self.n_ok += 1
        return httpx.Response(200, json={})


def _limiter(clock: FakeClock) -> AdaptiveRateLimiter:
    return AdaptiveRateLimiter(
        MAX, floor=FLOOR, quiet_seconds=QUIET, step=STEP, clock=clock.now, sleep=clock.sleep
    )


def _client(server: Any, limiter: AdaptiveRateLimiter) -> PublicClient:
    http = CFG.http.model_copy(
        update={
            "backoff_initial_seconds": CFG.http.backoff_initial_seconds.model_copy(
                update={"value": 0}
            ),
            "backoff_max_seconds": CFG.http.backoff_max_seconds.model_copy(update={"value": 0}),
            "max_attempts": CFG.http.max_attempts.model_copy(update={"value": 20}),
        }
    )
    c = PublicClient(http, rate_limiter=limiter)
    c._client = httpx.Client(transport=httpx.MockTransport(server))
    return c


def test_settings_are_sourced_and_ordered() -> None:
    for s in (
        KALSHI.min_requests_per_second,
        KALSHI.rate_recovery_quiet_seconds,
        KALSHI.rate_recovery_step_per_second,
    ):
        assert "2026-10-22" in s.source
    assert 0 < FLOOR < MAX and QUIET > 0 and STEP > 0


def test_starts_at_the_documented_rate() -> None:
    clock = FakeClock()
    assert _limiter(clock).rate == MAX
    assert kalshi_limiter(KALSHI).rate == MAX


def test_a_429_halves_the_rate_down_to_the_floor_only() -> None:
    clock = FakeClock()
    lim = _limiter(clock)
    rates = []
    for _ in range(12):
        lim.throttled()
        rates.append(lim.rate)
    assert rates[0] == MAX / 2
    assert rates[1] == MAX / 4
    assert min(rates) == FLOOR
    assert all(r >= FLOOR for r in rates)


def test_recovery_needs_a_full_quiet_period_and_steps_slowly_to_the_max() -> None:
    clock = FakeClock()
    lim = _limiter(clock)
    lim.throttled()
    low = lim.rate
    clock.t += QUIET - 0.001
    lim.ok()
    assert lim.rate == low  # not quiet long enough
    clock.t += 0.002
    lim.ok()
    assert lim.rate == min(MAX, low + STEP)
    lim.ok()
    assert lim.rate == min(MAX, low + STEP)  # one step per quiet period
    for _ in range(1000):
        clock.t += QUIET
        lim.ok()
    assert lim.rate == MAX


def test_against_a_server_with_a_lower_limit_the_rate_settles_and_429s_stay_few() -> None:
    clock = FakeClock()
    threshold = 5  # requests per second the fake server allows, far below MAX
    server = FakeServer(clock, threshold)
    lim = _limiter(clock)
    c = _client(server, lim)
    n = 600
    for i in range(n):
        c.get_json(f"https://example.test/{i}")
    assert server.n_ok == n  # every request eventually succeeded
    assert c.retryable_by_status[429] == server.n_429
    # the first burst costs at most the halvings from MAX to the floor; after that only a
    # recovery step (one per quiet period) can overshoot
    halvings = math.ceil(math.log2(MAX / FLOOR)) + 1
    assert server.n_429 <= halvings + int((clock.t - 1000.0) / QUIET) + 1
    assert lim.min_rate <= threshold
    assert lim.rate >= FLOOR
    # without adaptation the same server would refuse most requests at MAX
    assert server.n_429 < n * (1 - threshold / MAX)


def test_a_permissive_server_never_slows_the_limiter() -> None:
    clock = FakeClock()
    server = FakeServer(clock, threshold=10_000)
    lim = _limiter(clock)
    c = _client(server, lim)
    for i in range(200):
        c.get_json(f"https://example.test/{i}")
    assert server.n_429 == 0
    assert lim.rate == MAX and lim.min_rate == MAX


def test_run_summary_reports_the_effective_rate() -> None:
    s = KalshiRunStats(requests=10, http_429=1, rate_final=5.0, rate_min=2.5)
    text = s.summary()
    assert "rate 5.0 req/s (min 2.5)" in text
