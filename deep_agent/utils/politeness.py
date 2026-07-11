"""Scraper politeness: robots.txt compliance and per-domain rate limiting.

Both helpers are process-local (caches and last-request timestamps live in
module state), so under distributed Celery workers the throttle is enforced
per worker rather than globally — sufficient for polite crawling in eager
mode and a reasonable per-worker guard otherwise.
"""
from __future__ import annotations

import threading
import time
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

from deep_agent.utils.logging import get_logger

logger = get_logger("utils.politeness")

_ROBOTS_CACHE: dict[str, RobotFileParser] = {}
_ROBOTS_LOCK = threading.Lock()

_LAST_REQUEST: dict[str, float] = {}
_THROTTLE_LOCK = threading.Lock()


def _origin(url: str) -> str:
    """Return the scheme://host[:port] origin for ``url``."""

    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def _load_robots(origin: str, user_agent: str, timeout: int) -> RobotFileParser:
    """Fetch and parse robots.txt for an origin (cached, fail-open)."""

    parser = RobotFileParser()
    robots_url = f"{origin}/robots.txt"
    try:
        resp = httpx.get(
            robots_url,
            headers={"User-Agent": user_agent},
            timeout=timeout,
            follow_redirects=True,
        )
        if resp.status_code >= 400:
            # Missing/blocked robots.txt -> allow everything (standard behaviour).
            parser.parse([])
        else:
            parser.parse(resp.text.splitlines())
    except Exception as exc:  # noqa: BLE001 - fail open on fetch errors
        logger.debug("Could not fetch %s (%s); allowing by default", robots_url, exc)
        parser.parse([])
    return parser


def robots_allowed(url: str, user_agent: str, timeout: int = 10) -> bool:
    """Return whether ``user_agent`` may fetch ``url`` per its robots.txt."""

    origin = _origin(url)
    with _ROBOTS_LOCK:
        parser = _ROBOTS_CACHE.get(origin)
        if parser is None:
            parser = _load_robots(origin, user_agent, timeout)
            _ROBOTS_CACHE[origin] = parser
    return parser.can_fetch(user_agent, url)


def throttle(url: str, delay: float) -> None:
    """Block until at least ``delay`` seconds have passed for this domain."""

    if delay <= 0:
        return
    host = urlsplit(url).netloc
    with _THROTTLE_LOCK:
        now = time.monotonic()
        wait = delay - (now - _LAST_REQUEST.get(host, 0.0))
        if wait > 0:
            logger.debug("Throttling %s for %.2fs", host, wait)
            time.sleep(wait)
        _LAST_REQUEST[host] = time.monotonic()


def reset_state() -> None:
    """Clear caches/timers (primarily for tests)."""

    with _ROBOTS_LOCK:
        _ROBOTS_CACHE.clear()
    with _THROTTLE_LOCK:
        _LAST_REQUEST.clear()
