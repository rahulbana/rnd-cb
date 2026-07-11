"""Reusable Tenacity retry policies.

Keeping retry configuration in one place lets every network-bound call
(scraping, provider APIs) share consistent, well-logged back-off behaviour.
"""
from __future__ import annotations

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from deep_agent.utils.logging import get_logger

logger = get_logger("utils.retry")

# Exceptions that are typically transient and worth retrying.
_TRANSIENT_ERRORS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.RemoteProtocolError,
)


def _log_before_retry(retry_state) -> None:  # pragma: no cover - logging only
    logger.warning(
        "Retrying %s (attempt %d) after error: %s",
        retry_state.fn.__name__ if retry_state.fn else "call",
        retry_state.attempt_number,
        retry_state.outcome.exception() if retry_state.outcome else "n/a",
    )


def http_retry(max_attempts: int = 3):
    """Return a Tenacity decorator with exponential back-off for HTTP calls.

    Args:
        max_attempts: Total attempts before giving up.
    """

    return retry(
        reraise=True,
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        retry=retry_if_exception_type(_TRANSIENT_ERRORS),
        before_sleep=_log_before_retry,
    )
