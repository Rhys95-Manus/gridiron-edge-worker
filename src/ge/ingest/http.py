"""One HTTP client for every public source: timeout, retries and backoff from config/ingest.yaml.

Retries on network errors, 429 and 5xx. A Retry-After header, when sent, sets the wait."""

from __future__ import annotations

import logging
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


class PublicClient:
    """GET-only client. No auth headers are ever set (CLAUDE.md rule 8)."""

    def __init__(self, cfg: HttpSettings, user_agent: str | None = None) -> None:
        headers = {"Accept-Encoding": "gzip, deflate"}
        if user_agent:
            headers["User-Agent"] = user_agent
        self._client = httpx.Client(
            headers=headers, timeout=cfg.timeout_seconds.value, follow_redirects=False
        )
        self._get = retry(
            retry=retry_if_exception(_retryable),
            stop=stop_after_attempt(cfg.max_attempts.value),
            wait=_make_wait(cfg),
            reraise=True,
        )(self._get_once)

    def _get_once(self, url: str, params: dict[str, Any] | None) -> httpx.Response:
        r = self._client.get(url, params=params)
        if r.status_code == 429 or r.status_code >= 500:
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
