"""Query-history persistence backed by SQLite."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ..schemas import HistoryItem

_SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    question    TEXT    NOT NULL,
    sql         TEXT    NOT NULL,
    explanation TEXT    NOT NULL DEFAULT '',
    dialect     TEXT    NOT NULL DEFAULT '',
    valid       INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL
);
"""


class HistoryStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = str(Path(db_path))
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def add(
        self,
        question: str,
        sql: str,
        explanation: str,
        dialect: str,
        valid: bool,
    ) -> int:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO history (question, sql, explanation, dialect, valid, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (question, sql, explanation, dialect, int(valid), created_at),
            )
            return int(cur.lastrowid)

    def list(self, limit: int = 50, offset: int = 0) -> tuple[list[HistoryItem], int]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM history").fetchone()["c"]
            rows = conn.execute(
                "SELECT * FROM history ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._to_item(r) for r in rows], int(total)

    def get(self, item_id: int) -> HistoryItem | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM history WHERE id = ?", (item_id,)).fetchone()
        return self._to_item(row) if row else None

    def delete(self, item_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM history WHERE id = ?", (item_id,))
            return cur.rowcount > 0

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM history")

    @staticmethod
    def _to_item(row: sqlite3.Row) -> HistoryItem:
        return HistoryItem(
            id=row["id"],
            question=row["question"],
            sql=row["sql"],
            explanation=row["explanation"],
            dialect=row["dialect"],
            valid=bool(row["valid"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
