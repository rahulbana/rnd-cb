"""Database engine and session factory.

Uses SQLAlchemy so the backing store is a connection-string swap: SQLite for
local/dev (default), PostgreSQL for production
(``RAG_DATABASE_URL=postgresql+psycopg://…``). Nothing else in the app changes.
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from ..config import get_settings
from ..core.logging import get_logger

log = get_logger(__name__)


class Base(DeclarativeBase):
    pass


def _make_engine():
    settings = get_settings()
    url = settings.database_url
    connect_args = {}
    if url.startswith("sqlite"):
        # Ensure the parent directory exists for file-based SQLite.
        if url.startswith("sqlite:///"):
            path = url.replace("sqlite:///", "", 1)
            if path and path != ":memory:":
                os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        # FastAPI sync endpoints run in a threadpool, so allow cross-thread use.
        connect_args = {"check_same_thread": False}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True, future=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """Create tables if they don't exist. (For schema migrations in production,
    introduce Alembic; create_all is sufficient for this app's single table set.)"""
    from . import models  # noqa: F401  ensure models are registered

    Base.metadata.create_all(bind=engine)
    log.info("Database ready at %s", get_settings().database_url)


def get_db():
    """FastAPI dependency yielding a session with guaranteed cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
