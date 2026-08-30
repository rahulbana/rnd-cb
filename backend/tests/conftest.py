"""Shared test fixtures. Tests run fully offline (mock LLM provider)."""
from __future__ import annotations

import os
import tempfile

import pytest

# Force offline + isolated SQLite DB before app modules import settings.
os.environ.pop("OPENAI_API_KEY", None)
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402
from app.models.db import init_db  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db():
    init_db()
    yield
    try:
        os.close(_db_fd)
        os.remove(_db_path)
    except OSError:
        pass


@pytest.fixture()
def client():
    with TestClient(create_app()) as c:
        yield c
