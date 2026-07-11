"""SQLite storage for the chat archive and long-term memories.

This module owns the raw persistence layer:

* ``messages``          - a full archive of every message from every user.
* ``long_term_memory``  - durable per-user facts with vector embeddings.

The LangGraph short-term checkpointer keeps its own tables in the same file
but manages them independently (see ``agent.py``).
"""

from __future__ import annotations

import sqlite3
import time
from typing import Iterable


SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    TEXT    NOT NULL,
    thread_id  TEXT    NOT NULL,
    role       TEXT    NOT NULL,          -- 'user' | 'assistant'
    content    TEXT    NOT NULL,
    created_at REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id, created_at);

CREATE TABLE IF NOT EXISTS long_term_memory (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    TEXT    NOT NULL,
    content    TEXT    NOT NULL,
    embedding  BLOB,                       -- float32 vector, may be NULL
    created_at REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memory_user ON long_term_memory(user_id);
"""


class Database:
    """Thin wrapper around a shared SQLite connection."""

    def __init__(self, path: str) -> None:
        # check_same_thread=False so the connection can be reused across the
        # LangGraph node threads; WAL keeps it happy alongside the checkpointer.
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # -- chat archive -----------------------------------------------------

    def log_message(self, user_id: str, thread_id: str, role: str, content: str) -> None:
        self.conn.execute(
            "INSERT INTO messages (user_id, thread_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, thread_id, role, content, time.time()),
        )
        self.conn.commit()

    def recent_messages(self, user_id: str, limit: int = 20) -> list[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT role, content, created_at FROM messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        return list(reversed(cur.fetchall()))

    # -- long-term memory rows -------------------------------------------

    def insert_memory(self, user_id: str, content: str, embedding: bytes | None) -> int:
        cur = self.conn.execute(
            "INSERT INTO long_term_memory (user_id, content, embedding, created_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, content, embedding, time.time()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def all_memories(self, user_id: str) -> list[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT id, content, embedding, created_at FROM long_term_memory "
            "WHERE user_id = ? ORDER BY id",
            (user_id,),
        )
        return list(cur.fetchall())

    def known_users(self) -> Iterable[str]:
        cur = self.conn.execute(
            "SELECT DISTINCT user_id FROM messages "
            "UNION SELECT DISTINCT user_id FROM long_term_memory"
        )
        return [row[0] for row in cur.fetchall()]

    def close(self) -> None:
        self.conn.close()
