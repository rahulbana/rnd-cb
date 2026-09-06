"""Shared pytest fixtures."""

from __future__ import annotations

import shutil
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.core.ratelimit import get_rate_limiter
from app.core.registry import clear_registry_caches
from app.main import create_app

# Skip OCR-dependent tests cleanly where the tesseract binary is absent.
requires_tesseract = pytest.mark.skipif(
    shutil.which("tesseract") is None,
    reason="tesseract OCR binary not installed",
)


@pytest.fixture(autouse=True)
def _reset_caches():
    """Every test starts and ends with clean registry + rate-limiter caches."""
    clear_registry_caches()
    get_rate_limiter.cache_clear()
    yield
    clear_registry_caches()
    get_rate_limiter.cache_clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def async_env(tmp_path, monkeypatch) -> Callable[..., TestClient]:
    """Factory for a TestClient wired to a fully offline async ingestion stack.

    The registry (not request-injected deps) drives ingestion, exactly like the
    real worker: SQLite via the app's own engine, local-disk storage, the fake
    embedder + fake vector store, structure-aware chunking, the parser router,
    and a selectable task queue (``inline`` runs jobs in-process, ``fake`` only
    records them so the API stays non-blocking).
    """
    from app.core.config import settings
    from app.db import base as dbbase
    from app.db import models  # noqa: F401 - register tables on Base.metadata

    def _make(task_queue: str = "inline") -> TestClient:
        monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 't.db'}")
        monkeypatch.setattr(settings, "STORAGE_PROVIDER", "local_disk")
        monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path / "objects"))
        monkeypatch.setattr(settings, "LLM_PROVIDER", "fake")
        monkeypatch.setattr(settings, "EMBEDDER_PROVIDER", "fake")
        monkeypatch.setattr(settings, "VECTOR_STORE_PROVIDER", "fake")
        monkeypatch.setattr(settings, "RERANKER_PROVIDER", "fake")
        monkeypatch.setattr(settings, "CHUNKER_STRATEGY", "structure_aware")
        monkeypatch.setattr(settings, "PARSER_STRATEGY", "router")
        monkeypatch.setattr(settings, "TASK_QUEUE_PROVIDER", task_queue)
        monkeypatch.setattr(settings, "INGEST_BACKOFF_BASE", 0.0)

        dbbase.get_engine.cache_clear()
        dbbase._get_sessionmaker.cache_clear()
        clear_registry_caches()
        get_rate_limiter.cache_clear()

        dbbase.Base.metadata.create_all(dbbase.get_engine())
        return TestClient(create_app())

    yield _make

    dbbase.get_engine().dispose()
    dbbase.get_engine.cache_clear()
    dbbase._get_sessionmaker.cache_clear()


@pytest.fixture
def upload_client(async_env) -> TestClient:
    """Inline async stack: jobs complete in-process before upload returns."""
    return async_env("inline")
