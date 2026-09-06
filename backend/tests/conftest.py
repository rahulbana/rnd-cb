"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.registry import clear_registry_caches
from app.main import create_app


@pytest.fixture(autouse=True)
def _reset_registry():
    """Every test starts and ends with a clean registry cache."""
    clear_registry_caches()
    yield
    clear_registry_caches()


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())
