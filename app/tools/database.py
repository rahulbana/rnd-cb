"""SQL database tool (SQLite backend).

The backend is intentionally thin so it can be swapped for Postgres later:
replace ``_connect`` with a ``psycopg`` connection and the tool contract stays
identical. Queries are read-only by default; writes are gated behind
``DB_ALLOW_WRITES`` and a statement-type guard so the model can't silently
mutate data.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from .base import Tool, ToolRegistry

# Statement keywords we refuse when writes are disabled.
_WRITE_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create",
    "replace", "truncate", "attach", "detach", "pragma", "vacuum",
}


def _strip_sql(sql: str) -> str:
    """Remove comments/whitespace so the leading keyword check is reliable."""
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return sql.strip().rstrip(";").strip()


def _first_keyword(sql: str) -> str:
    stripped = _strip_sql(sql)
    return stripped.split(None, 1)[0].lower() if stripped else ""


def _statement_count(sql: str) -> int:
    body = _strip_sql(sql)
    # Naive but adequate: count non-empty statements after splitting on ';'.
    return len([s for s in body.split(";") if s.strip()])


def register(registry: ToolRegistry, config) -> None:
    db_path = Path(config.db_path)
    allow_writes = config.db_allow_writes

    def _connect() -> sqlite3.Connection:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # -- get_schema ---------------------------------------------------------
    def get_schema() -> str:
        if not db_path.exists():
            return (
                f"Database not found at '{db_path}'. "
                "Run `python scripts/init_db.py` to create and seed it."
            )
        with _connect() as conn:
            rows = conn.execute(
                "SELECT name, sql FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        if not rows:
            return "The database has no tables yet."
        return "\n\n".join(r["sql"] for r in rows if r["sql"])

    # -- run_sql ------------------------------------------------------------
    def run_sql(query: str, max_rows: int = 100) -> str:
        if not db_path.exists():
            return (
                f"Database not found at '{db_path}'. "
                "Run `python scripts/init_db.py` first."
            )
        if _statement_count(query) != 1:
            return "Error: submit exactly one SQL statement at a time."

        keyword = _first_keyword(query)
        is_write = keyword in _WRITE_KEYWORDS
        if is_write and not allow_writes:
            return (
                f"Error: write statements ('{keyword}') are disabled. "
                "This agent is read-only (set DB_ALLOW_WRITES=true to change)."
            )

        max_rows = max(1, min(int(max_rows), 1000))
        try:
            with _connect() as conn:
                cur = conn.execute(query)
                if cur.description is None:
                    conn.commit()
                    return f"OK. {cur.rowcount} row(s) affected."
                rows = cur.fetchmany(max_rows)
                columns = [d[0] for d in cur.description]
        except sqlite3.Error as exc:
            return f"SQL error: {exc}"

        if not rows:
            return "Query returned 0 rows."

        data = [dict(zip(columns, row)) for row in rows]
        note = ""
        if len(rows) == max_rows:
            note = f"\n(showing first {max_rows} rows; add LIMIT or refine the query for more)"
        import json

        return json.dumps({"columns": columns, "rows": data}, default=str) + note

    registry.register(
        Tool(
            name="db_get_schema",
            description=(
                "Return the CREATE TABLE statements for every table in the "
                "ecommerce database. Call this first to learn table and column "
                "names before writing SQL."
            ),
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            handler=get_schema,
        )
    )

    registry.register(
        Tool(
            name="db_run_sql",
            description=(
                "Execute a single SQL statement against the ecommerce SQLite "
                "database and return the rows as JSON. Read-only (SELECT) unless "
                "writes are explicitly enabled. Always inspect the schema with "
                "db_get_schema first if unsure about column names."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "One SQL statement (SQLite dialect).",
                    },
                    "max_rows": {
                        "type": "integer",
                        "description": "Maximum rows to return (default 100, max 1000).",
                        "default": 100,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            handler=run_sql,
        )
    )
