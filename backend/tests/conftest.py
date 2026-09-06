"""Shared pytest fixtures."""

from __future__ import annotations

import shutil

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.registry import clear_registry_caches
from app.main import create_app

# Skip OCR-dependent tests cleanly where the tesseract binary is absent.
requires_tesseract = pytest.mark.skipif(
    shutil.which("tesseract") is None,
    reason="tesseract OCR binary not installed",
)


@pytest.fixture(autouse=True)
def _reset_registry():
    """Every test starts and ends with a clean registry cache."""
    clear_registry_caches()
    yield
    clear_registry_caches()


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def db_sessionmaker(tmp_path):
    """A SQLite-backed sessionmaker with the schema created."""
    from app.db import models  # noqa: F401 - register tables on Base.metadata
    from app.db.base import Base

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    yield maker
    engine.dispose()


@pytest.fixture
def upload_client(tmp_path, db_sessionmaker) -> TestClient:
    """A TestClient wired to SQLite, local-disk storage, and the real router."""
    from app.adapters.parsers import ParserRouter
    from app.adapters.storage import LocalDiskStorage
    from app.api.v1.deps import parser as parser_dep
    from app.api.v1.deps import storage as storage_dep
    from app.core.config import settings
    from app.core.registry import build_parser_chain
    from app.db.base import get_db

    app = create_app()

    def _get_db():
        db = db_sessionmaker()
        try:
            yield db
        finally:
            db.close()

    storage_obj = LocalDiskStorage(str(tmp_path / "objects"))
    router = ParserRouter(build_parser_chain(settings))

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[storage_dep] = lambda: storage_obj
    app.dependency_overrides[parser_dep] = lambda: router
    return TestClient(app)
