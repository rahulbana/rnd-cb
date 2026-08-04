"""Postgres connection pool with a graceful no-DB fallback."""
from __future__ import annotations

import os
from pathlib import Path

import asyncpg

from .config import database_url

_pool: asyncpg.Pool | None = None
_connected = False

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


async def init_db() -> bool:
    """Create the pool and ensure the schema. Returns True if connected."""
    global _pool, _connected

    url = database_url()
    if not url:
        print("[db] DATABASE_URL not set — running without persistence.")
        _connected = False
        return False

    try:
        _pool = await asyncpg.create_pool(dsn=url, min_size=1, max_size=5)
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        async with _pool.acquire() as conn:
            await conn.execute(schema)
        _connected = True
        print("[db] Connected and schema ensured.")
        return True
    except Exception as exc:  # noqa: BLE001 - persistence is optional
        print(f"[db] Failed to connect/initialize: {exc}")
        _pool = None
        _connected = False
        return False


async def close_db() -> None:
    global _pool, _connected
    if _pool is not None:
        await _pool.close()
        _pool = None
        _connected = False


def is_connected() -> bool:
    return _connected


def get_pool() -> asyncpg.Pool | None:
    return _pool
