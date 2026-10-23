"""One HTTP client for every public source: timeout, retries and backoff from config/ingest.yaml.

Retries on network errors, 429 and 5xx. A Retry-After header, when sent, sets the wait."""

from __future__ import annotations

import logging
import time
from collections import Counter
from collections.abc import Callable
from typing import Any

import httpx
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from ge.config import HttpSettings

log = logging.getLogger(__name__)


class RetryableStatus(Exception):
    def __init__(self, response: httpx.Response) -> None:
        super().__init__(f"HTTP {response.status_code} from {response.request.url}")
        self.response = response


def _retryable(exc: BaseException) -> bool:
    return isinstance(exc, RetryableStatus | httpx.TransportError)


def _make_wait(cfg: HttpSettings) -> Any:
    backoff = wait_exponential(
        multiplier=cfg.backoff_initial_seconds.value, max=cfg.backoff_max_seconds.value
    )

    def wait(state: RetryCallState) -> float:
        exc = state.outcome.exception() if state.outcome else None
        if isinstance(exc, RetryableStatus):
            header = exc.response.headers.get("retry-after", "")
            if header.isdigit():
                return float(header)
        return float(backoff(state))

    return wait


class RateLimiter:
    """Spaces request starts at least 1/rate seconds apart, with no bursts (DATA-08 request
    budget, 2026-10-20). Clock and sleep are injectable for tests."""

    def __init__(
        self,
        per_second: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if per_second <= 0:
            raise ValueError("rate must be positive")
        self._interval = 1.0 / per_second
        self._clock = clock
        self._sleep = sleep
        self._next: float | None = None

    @property
    def rate(self) -> float:
        return 1.0 / self._interval

    def wait(self) -> None:
        now = self._clock()
        if self._next is not None and now < self._next:
            self._sleep(self._next - now)
            now = self._next
        self._next = now + self._interval

    def throttled(self) -> None:
        """Called after a 429. A fixed limiter keeps its rate."""

    def ok(self) -> None:
        """Called after a successful response. A fixed limiter keeps its rate."""


class AdaptiveRateLimiter(RateLimiter):
    """DATA-08 (ruling 2026-10-22): halve the rate on every 429, never below `floor`; after
    `quiet_seconds` with no 429, raise it by `step` requests/s, at most once per quiet period
    and never above the starting (maximum) rate. Every change is logged."""

    def __init__(
        self,
        per_second: float,
        *,
        floor: float,
        quiet_seconds: float,
        step: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not 0 < floor <= per_second or quiet_seconds <= 0 or step <= 0:
            raise ValueError("need 0 < floor <= rate, quiet_seconds > 0, step > 0")
        super().__init__(per_second, clock=clock, sleep=sleep)
        self._max = per_second
        self._floor = floor
        self._quiet = quiet_seconds
        self._step = step
        self._calm_since = clock()
        self.min_rate = per_second

    def _set(self, rate: float, why: str) -> None:
        old = self.rate
        self._interval = 1.0 / rate
        self.min_rate = min(self.min_rate, rate)
        if rate != old:
            log.warning("rate limit %s: %.2f -> %.2f req/s", why, old, rate)

    def throttled(self) -> None:
        self._set(max(self._floor, self.rate / 2), "after HTTP 429")
        self._calm_since = self._clock()

    def ok(self) -> None:
        now = self._clock()
        if self.rate < self._max and now - self._calm_since >= self._quiet:
            self._set(min(self._max, self.rate + self._step), "recovering")
            self._calm_since = now


class PublicClient:
    """GET-only client. No auth headers are ever set (CLAUDE.md rule 8). Counts every
    attempt and every retryable status, so a run can report its request load."""

    def __init__(
        self,
        cfg: HttpSettings,
        user_agent: str | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        headers = {"Accept-Encoding": "gzip, deflate"}
        if user_agent:
            headers["User-Agent"] = user_agent
        self._client = httpx.Client(
            headers=headers, timeout=cfg.timeout_seconds.value, follow_redirects=False
        )
        self._limiter = rate_limiter
        self.attempts = 0
        self.retryable_by_status: Counter[int] = Counter()
        self._get = retry(
            retry=retry_if_exception(_retryable),
            stop=stop_after_attempt(cfg.max_attempts.value),
            wait=_make_wait(cfg),
            reraise=True,
        )(self._get_once)

    def _get_once(self, url: str, params: dict[str, Any] | None) -> httpx.Response:
        if self._limiter is not None:
            self._limiter.wait()
        self.attempts += 1
        r = self._client.get(url, params=params)
        if r.status_code == 429 or r.status_code >= 500:
            self.retryable_by_status[r.status_code] += 1
            if r.status_code == 429 and self._limiter is not None:
                self._limiter.throttled()
            log.warning("retryable HTTP %s from %s", r.status_code, r.request.url.host)
            raise RetryableStatus(r)
        if self._limiter is not None:
            self._limiter.ok()
        return r

    def get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """GET with retries. Returns non-retryable responses (e.g. 404) to the caller."""
        return self._get(url, params)

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        r = self.get(url, params)
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PublicClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
