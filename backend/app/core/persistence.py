"""Postgres persistence: connection pool + LangGraph checkpointer lifecycle.

For a long-lived service we do NOT use ``AsyncPostgresSaver.from_conn_string``
per request (that context manager closes the connection on exit). Instead we own
a single ``AsyncConnectionPool`` for the process lifetime and hand it to the
saver. ``setup()`` runs the checkpointer's schema migrations once at startup.

Note the required connection kwargs for the pipeline the saver uses:
``autocommit=True`` and ``prepare_threshold=0``.
"""
from __future__ import annotations

import logging

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from app.core.config import Settings

logger = logging.getLogger(__name__)


class Persistence:
    def __init__(self) -> None:
        self._pool: AsyncConnectionPool | None = None
        self._checkpointer: AsyncPostgresSaver | None = None

    @property
    def checkpointer(self) -> AsyncPostgresSaver:
        if self._checkpointer is None:
            raise RuntimeError("Persistence not started. Call open() first.")
        return self._checkpointer

    async def open(self, settings: Settings) -> None:
        self._pool = AsyncConnectionPool(
            conninfo=settings.database_url,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            open=False,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        await self._pool.open(wait=True)
        self._checkpointer = AsyncPostgresSaver(self._pool)
        # Idempotent: creates checkpointer tables / runs migrations if needed.
        await self._checkpointer.setup()
        logger.info("persistence initialized", extra={"pool_max": settings.db_pool_max_size})

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            self._checkpointer = None
            logger.info("persistence closed")
