"""SQL formatting and validation utilities.

The system is intentionally *read-only*: only SELECT / WITH(...SELECT) queries
are accepted. Any statement that could mutate data or schema is rejected.
"""
from __future__ import annotations

import sqlparse
import sqlglot
from sqlglot import exp

from ..schemas import ValidationResult

# Statement types (top-level expression classes) that read data only.
READ_ONLY_EXPRESSIONS = (exp.Select, exp.Union, exp.Subquery)

# Expression classes that write/modify data or schema — always rejected.
WRITE_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.Merge,
    exp.Command,  # catch-all for GRANT, TRUNCATE, CALL, etc.
)

# Keywords that must never appear, even nested (defense in depth).
FORBIDDEN_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "truncate",
    "alter",
    "create",
    "replace",
    "merge",
    "grant",
    "revoke",
    "attach",
    "pragma",
    "vacuum",
    "call",
    "execute",
    "exec",
}


def format_sql(sql: str, dialect: str | None = None) -> str:
    """Pretty-print SQL. Tries sqlglot first, falls back to sqlparse."""
    sql = sql.strip().rstrip(";").strip()
    if not sql:
        return ""

    if dialect:
        try:
            parsed = sqlglot.parse_one(sql, read=dialect)
            return parsed.sql(dialect=dialect, pretty=True)
        except Exception:
            pass

    # Dialect-agnostic fallback.
    return sqlparse.format(
        sql,
        reindent=True,
        keyword_case="upper",
        identifier_case=None,
        strip_comments=False,
    ).strip()


def _statement_type(expression: exp.Expression) -> str:
    return type(expression).__name__.upper()


def validate_sql(sql: str, dialect: str | None = None) -> ValidationResult:
    """Parse SQL and confirm it is syntactically valid and read-only."""
    errors: list[str] = []
    warnings: list[str] = []
    cleaned = sql.strip().rstrip(";").strip()

    if not cleaned:
        return ValidationResult(
            valid=False,
            read_only=False,
            statement_type=None,
            errors=["Query is empty."],
        )

    # Reject multiple statements outright.
    statements = [s for s in sqlparse.parse(cleaned) if str(s).strip()]
    if len(statements) > 1:
        errors.append("Multiple statements are not allowed; submit a single query.")

    # Parse with sqlglot for structural analysis.
    expression: exp.Expression | None = None
    try:
        expression = sqlglot.parse_one(cleaned, read=dialect) if dialect else sqlglot.parse_one(cleaned)
    except Exception as exc:  # sqlglot ParseError and friends
        errors.append(f"Syntax error: {exc}")

    statement_type: str | None = None
    read_only = False

    if expression is not None:
        statement_type = _statement_type(expression)

        if isinstance(expression, WRITE_EXPRESSIONS):
            errors.append(
                f"Only read-only SELECT queries are allowed; got {statement_type}."
            )
        elif isinstance(expression, READ_ONLY_EXPRESSIONS) or statement_type in {
            "SELECT",
            "UNION",
            "WITH",
        }:
            read_only = True
        else:
            errors.append(
                f"Statement type {statement_type} is not permitted in read-only mode."
            )

        # Defense in depth: scan every token for forbidden keywords.
        for token in expression.walk():
            node = token[0] if isinstance(token, tuple) else token
            if isinstance(node, exp.Command):
                read_only = False
                errors.append(f"Forbidden command detected: {node.sql()}")

    # Keyword scan on the raw text as a final backstop.
    lowered_tokens = {
        t.value.lower()
        for stmt in statements
        for t in stmt.flatten()
        if t.ttype in (sqlparse.tokens.Keyword, sqlparse.tokens.Keyword.DDL, sqlparse.tokens.Keyword.DML)
    }
    hit = lowered_tokens & FORBIDDEN_KEYWORDS
    if hit:
        read_only = False
        errors.append(f"Forbidden keyword(s) present: {', '.join(sorted(hit))}.")

    # Advisory: SELECT * and missing LIMIT.
    if read_only and not errors:
        if "*" in cleaned and "count(" not in cleaned.lower():
            warnings.append("Query uses SELECT * — consider selecting explicit columns.")
        if "limit" not in cleaned.lower():
            warnings.append("Query has no LIMIT — it may return a large result set.")

    valid = not errors
    return ValidationResult(
        valid=valid,
        read_only=read_only and valid,
        statement_type=statement_type,
        errors=errors,
        warnings=warnings,
    )
