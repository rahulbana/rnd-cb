"""Lightweight in-process rate limiter (fixed sliding window).

Caps how many ingestion jobs can be enqueued per window. Single-process and
single-tenant today; Phase 9 adds per-provider limits and a distributed
backend. Deliberately simple and dependency-free.
"""

from __future__ import annotations

import time
from collections import deque
from functools import lru_cache

from app.core.config import settings


class RateLimiter:
    """Allows at most ``limit`` events per rolling ``window`` seconds."""

    def __init__(self, limit: int, window: float) -> None:
        self._limit = limit
        self._window = window
        self._hits: deque[float] = deque()

    def allow(self, n: int = 1) -> bool:
        """Try to consume ``n`` slots; return False if it would exceed the limit."""
        now = time.monotonic()
        cutoff = now - self._window
        while self._hits and self._hits[0] <= cutoff:
            self._hits.popleft()
        if len(self._hits) + n > self._limit:
            return False
        self._hits.extend([now] * n)
        return True


@lru_cache
def get_rate_limiter() -> RateLimiter:
    return RateLimiter(settings.INGEST_RATE_LIMIT, settings.INGEST_RATE_WINDOW_SECONDS)
