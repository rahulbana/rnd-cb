"""SQLite persistence for notes. Thread-safe via a per-call connection."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from ..config import config


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they do not exist."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT NOT NULL,
                body       TEXT NOT NULL DEFAULT '',
                tags       TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT NOT NULL DEFAULT 'New chat',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role            TEXT NOT NULL,
                content         TEXT NOT NULL,
                created_at      TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                    ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_conv "
            "ON messages(conversation_id, id)"
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def create_note(title: str, body: str = "", tags: str = "") -> dict:
    ts = _now()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO notes (title, body, tags, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, body, tags, ts, ts),
        )
        note_id = cur.lastrowid
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        return _row_to_dict(row)


def list_notes(limit: int = 100) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM notes ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def search_notes(query: str, limit: int = 100) -> list[dict]:
    like = f"%{query}%"
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM notes WHERE title LIKE ? OR body LIKE ? OR tags LIKE ? "
            "ORDER BY updated_at DESC LIMIT ?",
            (like, like, like, limit),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def delete_note(note_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        return cur.rowcount > 0


def get_note(note_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        return _row_to_dict(row) if row else None


# ------------------------------ Conversations ------------------------------

def create_conversation(title: str = "New chat") -> dict:
    ts = _now()
    title = (title or "New chat").strip()[:80] or "New chat"
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO conversations (title, created_at, updated_at) "
            "VALUES (?, ?, ?)",
            (title, ts, ts),
        )
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return _row_to_dict(row)


def list_conversations(limit: int = 100) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def get_conversation(conv_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None


def rename_conversation(conv_id: int, title: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title.strip()[:80] or "New chat", _now(), conv_id),
        )
        return cur.rowcount > 0


def touch_conversation(conv_id: int) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?", (_now(), conv_id)
        )


def delete_conversation(conv_id: int) -> bool:
    with _connect() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        cur = conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        return cur.rowcount > 0


def add_message(conv_id: int, role: str, content: str) -> dict:
    ts = _now()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (conv_id, role, content, ts),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?", (ts, conv_id)
        )
        row = conn.execute(
            "SELECT * FROM messages WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return _row_to_dict(row)


def get_messages(conv_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY id ASC",
            (conv_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
