"""SQLite storage layer for client records.

A thin, dependency-free data-access layer. Each call opens its own short-lived
connection so the layer is safe to use from FastMCP's worker threads without
sharing a connection across threads.
"""

from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

_SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL,
    country        TEXT,
    state          TEXT,
    city           TEXT,
    contact_number TEXT,
    email          TEXT,
    notes          TEXT,
    created_at     TEXT    NOT NULL,
    updated_at     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_clients_country ON clients(country);
CREATE INDEX IF NOT EXISTS idx_clients_city    ON clients(city);
CREATE INDEX IF NOT EXISTS idx_clients_name    ON clients(name);
"""

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Fields a caller is allowed to write. Keeps update logic injection-safe by
# whitelisting column names rather than interpolating arbitrary keys.
_MUTABLE_FIELDS = ("name", "country", "state", "city", "contact_number", "email", "notes")

# Fields that must be present and non-empty when creating a client.
_REQUIRED_FIELDS = ("name", "country", "state", "email")


class ClientStore:
    """CRUD + search over the ``clients`` table."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        parent = os.path.dirname(os.path.abspath(db_path))
        os.makedirs(parent, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    # ---- helpers ----
    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _validate_email(email: str | None) -> None:
        if email and not _EMAIL_RE.match(email):
            raise ValueError(f"Invalid email address: {email!r}")

    # ---- create ----
    def add_client(
        self,
        name: str,
        country: str,
        state: str,
        email: str,
        city: str | None = None,
        contact_number: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        # name, country, state, email are mandatory and must be non-empty.
        missing = [
            field
            for field, value in (
                ("name", name),
                ("country", country),
                ("state", state),
                ("email", email),
            )
            if value is None or not str(value).strip()
        ]
        if missing:
            raise ValueError(f"Missing required field(s): {', '.join(missing)}")
        self._validate_email(email)
        now = self._now()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO clients
                    (name, country, state, city, contact_number, email, notes,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name.strip(), country, state, city, contact_number, email, notes, now, now),
            )
            return self._get(conn, cur.lastrowid)

    # ---- read ----
    def get_client(self, client_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            return self._get(conn, client_id)

    def list_clients(
        self,
        country: str | None = None,
        state: str | None = None,
        city: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for col, val in (("country", country), ("state", state), ("city", city)):
            if val:
                clauses.append(f"{col} = ? COLLATE NOCASE")
                params.append(val)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        limit = max(1, min(int(limit), 500))
        params.extend([limit, max(0, int(offset))])
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM clients {where} ORDER BY id DESC LIMIT ? OFFSET ?",
                params,
            ).fetchall()
            return [dict(r) for r in rows]

    def search_clients(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Case-insensitive substring match across the main text fields."""
        if not query or not query.strip():
            return []
        like = f"%{query.strip()}%"
        limit = max(1, min(int(limit), 500))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM clients
                WHERE name LIKE ? COLLATE NOCASE
                   OR country LIKE ? COLLATE NOCASE
                   OR state LIKE ? COLLATE NOCASE
                   OR city LIKE ? COLLATE NOCASE
                   OR contact_number LIKE ?
                   OR email LIKE ? COLLATE NOCASE
                ORDER BY id DESC LIMIT ?
                """,
                (like, like, like, like, like, like, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    # ---- update ----
    def update_client(self, client_id: int, **fields: Any) -> dict[str, Any] | None:
        updates = {k: v for k, v in fields.items() if k in _MUTABLE_FIELDS and v is not None}
        if not updates:
            # Nothing to change; return current state (or None if absent).
            return self.get_client(client_id)
        if "email" in updates:
            self._validate_email(updates["email"])
        if "name" in updates and not str(updates["name"]).strip():
            raise ValueError("`name` cannot be set to empty.")

        set_clause = ", ".join(f"{col} = ?" for col in updates)
        params = list(updates.values())
        params.append(self._now())  # updated_at
        params.append(client_id)
        with self._connect() as conn:
            if self._get(conn, client_id) is None:
                return None
            conn.execute(
                f"UPDATE clients SET {set_clause}, updated_at = ? WHERE id = ?",
                params,
            )
            return self._get(conn, client_id)

    # ---- delete ----
    def delete_client(self, client_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
            return cur.rowcount > 0

    def count(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]

    # ---- internal ----
    @staticmethod
    def _get(conn: sqlite3.Connection, client_id: int) -> dict[str, Any] | None:
        row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        return dict(row) if row else None
