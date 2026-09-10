"""Offline tests for the validation layer (no API key required).

Run from the backend/ directory with the venv active:

    python -m pytest         # if pytest is installed
    python tests/test_validator.py   # standalone runner
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.validator import SchemaInvalidError, validate  # noqa: E402

SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "email": {"type": "string"},
        "age": {"type": "integer", "minimum": 0},
    },
    "required": ["name", "email", "age"],
    "additionalProperties": False,
}


def test_valid_object_has_no_errors():
    data = {"name": "Rahul", "email": "rahul@example.com", "age": 35}
    assert validate(data, SCHEMA) == []


def test_wrong_type_is_reported():
    data = {"name": "Rahul", "email": "rahul@example.com", "age": "old"}
    errors = validate(data, SCHEMA)
    assert any(e["path"] == "age" for e in errors)


def test_missing_required_field_is_reported():
    data = {"name": "Rahul"}
    errors = validate(data, SCHEMA)
    assert len(errors) >= 1


def test_additional_property_is_reported():
    data = {
        "name": "Rahul",
        "email": "rahul@example.com",
        "age": 35,
        "extra": True,
    }
    errors = validate(data, SCHEMA)
    assert len(errors) >= 1


def test_invalid_schema_raises():
    try:
        validate({}, {"type": "not-a-real-type"})
    except SchemaInvalidError:
        return
    raise AssertionError("expected SchemaInvalidError")


if __name__ == "__main__":
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok - {name}")
            passed += 1
    print(f"\n{passed} tests passed")
