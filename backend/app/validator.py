"""JSON Schema validation helpers."""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


class SchemaInvalidError(ValueError):
    """Raised when a user-supplied JSON Schema is itself invalid."""


def _format_path(error) -> str:
    """Turn a jsonschema error path into a readable dotted string."""
    if not error.absolute_path:
        return "(root)"
    parts: list[str] = []
    for segment in error.absolute_path:
        if isinstance(segment, int):
            parts.append(f"[{segment}]")
        elif parts:
            parts.append(f".{segment}")
        else:
            parts.append(str(segment))
    return "".join(parts)


def validate(data: Any, schema: dict[str, Any]) -> list[dict[str, str]]:
    """Validate ``data`` against ``schema``.

    Returns a list of ``{"path", "message"}`` dicts — empty when the data is
    valid. Raises :class:`SchemaInvalidError` if the schema itself is malformed.
    """
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise SchemaInvalidError(f"Provided JSON Schema is invalid: {exc.message}") from exc

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    return [
        {"path": _format_path(error), "message": error.message} for error in errors
    ]
