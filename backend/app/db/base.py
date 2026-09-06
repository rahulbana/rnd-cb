"""SQLAlchemy engine, session, and declarative base.

The engine is created lazily so importing models (in tests, Alembic
autogenerate, or tooling) never requires the DB driver or a live connection.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


@lru_cache
def get_engine() -> Engine:
    """Lazily create (and cache) the SQLAlchemy engine."""
    return create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)


@lru_cache
def _get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)


def SessionLocal() -> Session:
    """Return a new session from the lazily-built sessionmaker."""
    return _get_sessionmaker()()


def get_db():
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
