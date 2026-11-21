"""Small, explainable HTTP helper: timeouts, retries with backoff, circuit breaker.

Used by every external call (weather API, dataset download, optional LLM) so
network failures and rate limits degrade gracefully instead of crashing the app.
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field

import requests

from . import config

log = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class NetworkUnavailable(RuntimeError):
    """Raised when a call cannot be made (offline mode, open circuit, retries exhausted)."""


@dataclass
class CircuitBreaker:
    """After N consecutive failures, skip the service for a cooldown period."""

    max_failures: int = config.CIRCUIT_BREAKER_FAILS
    cooldown_s: float = config.CIRCUIT_BREAKER_COOLDOWN_S
    failures: int = 0
    opened_at: float | None = None

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        if time.monotonic() - self.opened_at >= self.cooldown_s:
            self.opened_at, self.failures = None, 0  # half-open: try again
            return True
        return False

    def record(self, ok: bool) -> None:
        if ok:
            self.failures, self.opened_at = 0, None
        else:
            self.failures += 1
            if self.failures >= self.max_failures:
                self.opened_at = time.monotonic()


@dataclass
class CallStats:
    calls: int = 0
    retries: int = 0
    failures: int = 0
    by_service: dict = field(default_factory=dict)


_breakers: dict[str, CircuitBreaker] = {}
STATS = CallStats()


def _backoff_delay(attempt: int, retry_after: str | None) -> float:
    """Exponential backoff with jitter; honour Retry-After from rate limiters."""
    if retry_after:
        try:
            return min(float(retry_after), 30.0)
        except ValueError:
            pass
    return min(0.5 * (2 ** attempt), 8.0) + random.uniform(0, 0.25)


def request_json(
    service: str,
    method: str,
    url: str,
    *,
    max_retries: int = config.HTTP_MAX_RETRIES,
    timeout: float = config.HTTP_TIMEOUT_S,
    sleep=time.sleep,
    session: requests.Session | None = None,
    **kwargs,
):
    """Make a JSON request with retries. Raises NetworkUnavailable on failure."""
    if not config.ALLOW_NETWORK:
        raise NetworkUnavailable("network disabled (ALLOW_NETWORK=0)")
    breaker = _breakers.setdefault(service, CircuitBreaker())
    if not breaker.allow():
        raise NetworkUnavailable(f"{service}: circuit open after repeated failures")

    http = session or requests
    last_err: Exception | None = None
    for attempt in range(max_retries):
        STATS.calls += 1
        STATS.by_service[service] = STATS.by_service.get(service, 0) + 1
        try:
            resp = http.request(method, url, timeout=timeout, **kwargs)
            if resp.status_code in RETRYABLE_STATUS:
                last_err = RuntimeError(f"HTTP {resp.status_code}")
                delay = _backoff_delay(attempt, resp.headers.get("Retry-After"))
            elif resp.status_code >= 400:
                breaker.record(False)
                STATS.failures += 1
                raise NetworkUnavailable(f"{service}: HTTP {resp.status_code}")
            else:
                breaker.record(True)
                return resp.json() if "json" in resp.headers.get("Content-Type", "json") else resp.text
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_err = type(exc).__name__  # short, user-facing reason
            delay = _backoff_delay(attempt, None)
        if attempt < max_retries - 1:
            STATS.retries += 1
            log.warning("%s attempt %d failed (%s); retrying in %.1fs", service, attempt + 1, last_err, delay)
            sleep(delay)

    breaker.record(False)
    STATS.failures += 1
    raise NetworkUnavailable(f"{service}: failed after {max_retries} attempts ({last_err})")


def download_text(service: str, url: str, **kwargs) -> str:
    """Download a text file (e.g. CSV) with the same retry rules."""
    if not config.ALLOW_NETWORK:
        raise NetworkUnavailable("network disabled (ALLOW_NETWORK=0)")
    breaker = _breakers.setdefault(service, CircuitBreaker())
    if not breaker.allow():
        raise NetworkUnavailable(f"{service}: circuit open")
    last_err = None
    for attempt in range(config.HTTP_MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=config.HTTP_TIMEOUT_S * 3, **kwargs)
            if resp.ok:
                breaker.record(True)
                return resp.text
            last_err = RuntimeError(f"HTTP {resp.status_code}")
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_err = type(exc).__name__
        time.sleep(_backoff_delay(attempt, None))
    breaker.record(False)
    raise NetworkUnavailable(f"{service}: download failed ({last_err})")
