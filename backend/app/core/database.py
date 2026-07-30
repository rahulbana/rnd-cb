"""Async SQLAlchemy engine, session factory and declarative base."""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with SessionLocal() as session:
        yield session


def _add_missing_columns(sync_conn) -> None:
    """Lightweight additive migration.

    ``create_all`` only creates missing *tables*, never new columns on an
    existing one — so a DB created by an older version is missing columns
    added later (e.g. ``sources``). This inspects each table and issues an
    ``ALTER TABLE ... ADD COLUMN`` for any column present on the model but
    not in the database. Columns are added as nullable with a sensible
    server default so existing rows stay valid. Idempotent; a real Alembic
    setup should replace this before production.
    """
    from sqlalchemy import JSON, String, Text, inspect, text

    inspector = inspect(sync_conn)
    dialect = sync_conn.dialect
    existing_tables = set(inspector.get_table_names())

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing_cols:
                continue
            col_type = col.type.compile(dialect=dialect)
            if isinstance(col.type, JSON):
                default_sql = "'[]'"
            elif isinstance(col.type, (String, Text)):
                default_sql = "''"
            else:
                default_sql = None
            ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col_type}'
            if default_sql is not None:
                ddl += f" DEFAULT {default_sql}"
            logging.getLogger(__name__).info(
                "Migrating: adding column %s.%s", table.name, col.name
            )
            sync_conn.execute(text(ddl))


async def init_db() -> None:
    """Create tables and apply lightweight additive migrations.

    For real deployments prefer Alembic migrations.
    """
    # Import models so they are registered on the metadata.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)
