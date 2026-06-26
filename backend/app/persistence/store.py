"""Run-history persistence.

A small abstraction with a SQLite implementation (single table, JSON blob per
run) and a no-op implementation for when persistence is disabled. SQLite calls
run in a worker thread so they don't block the event loop.
"""
from __future__ import annotations

import abc
import asyncio
import json
import sqlite3
import threading
from pathlib import Path
from typing import List, Optional

from ..core.config import Settings
from ..core.logging import get_logger
from .models import RunRecord, RunSummary

logger = get_logger(__name__)


class RunStore(abc.ABC):
    @abc.abstractmethod
    async def save(self, record: RunRecord) -> None: ...

    @abc.abstractmethod
    async def get(self, run_id: str) -> Optional[RunRecord]: ...

    @abc.abstractmethod
    async def list(self, limit: int = 50) -> List[RunSummary]: ...


class NullRunStore(RunStore):
    """Used when persistence is disabled — silently drops everything."""

    async def save(self, record: RunRecord) -> None:
        return None

    async def get(self, run_id: str) -> Optional[RunRecord]:
        return None

    async def list(self, limit: int = 50) -> List[RunSummary]:
        return []


class SQLiteRunStore(RunStore):
    def __init__(self, db_path: str) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_schema()
        logger.info("Run history persisted to %s", path.resolve())

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id          TEXT PRIMARY KEY,
                    query       TEXT NOT NULL,
                    status      TEXT NOT NULL,
                    started_at  REAL NOT NULL,
                    data        TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at DESC)"
            )
            self._conn.commit()

    # ---- sync helpers (run inside a worker thread) ----
    def _save_sync(self, record: RunRecord) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO runs (id, query, status, started_at, data) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    record.id,
                    record.query,
                    record.status,
                    record.started_at,
                    record.model_dump_json(),
                ),
            )
            self._conn.commit()

    def _get_sync(self, run_id: str) -> Optional[RunRecord]:
        with self._lock:
            row = self._conn.execute(
                "SELECT data FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
        return RunRecord.model_validate_json(row["data"]) if row else None

    def _list_sync(self, limit: int) -> List[RunSummary]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT data FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [RunSummary.from_record(RunRecord.model_validate_json(r["data"])) for r in rows]

    # ---- async API ----
    async def save(self, record: RunRecord) -> None:
        await asyncio.to_thread(self._save_sync, record)

    async def get(self, run_id: str) -> Optional[RunRecord]:
        return await asyncio.to_thread(self._get_sync, run_id)

    async def list(self, limit: int = 50) -> List[RunSummary]:
        return await asyncio.to_thread(self._list_sync, limit)


def build_run_store(settings: Settings) -> RunStore:
    if not settings.persist_runs:
        return NullRunStore()
    return SQLiteRunStore(settings.runs_db_path)
