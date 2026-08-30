"""Shared async HTTP client for tools that call external APIs.

Provides a pooled ``httpx.AsyncClient``, an in-memory TTL cache (spec section 23
— cache API responses), and a ``get_json`` helper that never raises: on any
network/parse error it returns ``None`` so callers degrade gracefully to
estimates (spec section 26).
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from ..config.logging import get_logger

logger = get_logger(__name__)

_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()

# key -> (expires_at, value)
_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = asyncio.Lock()

# key -> expires_at  (remember recent failures so one dead host doesn't slow a
# whole plan with repeated retries)
_neg_cache: dict[str, float] = {}
NEG_CACHE_TTL = 30.0

DEFAULT_TIMEOUT = 12.0
USER_AGENT = "TravelPlanner/1.0 (+https://github.com/rahulbana/rnd-cb)"


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        async with _client_lock:
            if _client is None:
                _client = httpx.AsyncClient(
                    timeout=DEFAULT_TIMEOUT,
                    headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                    follow_redirects=True,
                    # trust_env=True (default) picks up HTTPS_PROXY if present.
                )
    return _client


async def aclose() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def _cache_get(key: str) -> Any | None:
    async with _cache_lock:
        entry = _cache.get(key)
        if entry and entry[0] > time.time():
            return entry[1]
        if entry:
            _cache.pop(key, None)
    return None


async def _cache_set(key: str, value: Any, ttl: float) -> None:
    async with _cache_lock:
        _cache[key] = (time.time() + ttl, value)


async def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    ttl: float = 3600.0,
    timeout: float | None = None,
    retries: int = 1,
) -> Any | None:
    """GET JSON with caching + retry. Returns parsed JSON or ``None`` on failure."""
    cache_key = f"GET {url}?{sorted((params or {}).items())}"
    cached = await _cache_get(cache_key)
    if cached is not None:
        return cached
    if _neg_cache.get(cache_key, 0.0) > time.time():
        return None  # recently failed — don't hammer a dead host

    client = await get_client()
    delay = 0.5
    for attempt in range(retries + 1):
        try:
            resp = await client.get(url, params=params, headers=headers,
                                    timeout=timeout or DEFAULT_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            await _cache_set(cache_key, data, ttl)
            return data
        except Exception as exc:
            if attempt < retries:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            logger.warning("external GET failed (%s): %s", url, exc)
            _neg_cache[cache_key] = time.time() + NEG_CACHE_TTL
            return None
    return None


async def post_json(
    url: str,
    *,
    data: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
) -> Any | None:
    """POST returning JSON, or ``None`` on failure. Not cached."""
    client = await get_client()
    try:
        resp = await client.post(url, data=data, json=json_body, headers=headers,
                                 timeout=timeout or DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("external POST failed (%s): %s", url, exc)
        return None
