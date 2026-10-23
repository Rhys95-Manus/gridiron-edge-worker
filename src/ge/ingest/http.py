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

    def wait(self) -> None:
        now = self._clock()
        if self._next is not None and now < self._next:
            self._sleep(self._next - now)
            now = self._next
        self._next = now + self._interval


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
            log.warning("retryable HTTP %s from %s", r.status_code, r.request.url.host)
            raise RetryableStatus(r)
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
