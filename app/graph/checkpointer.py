"""Checkpointer factory.

Returns an async context manager yielding a LangGraph checkpointer:
  - Postgres (`AsyncPostgresSaver`) when DATABASE_URL is set — survives crashes,
    so a long run can resume from its last checkpoint by thread_id.
  - In-memory (`MemorySaver`) otherwise — fine for dev, no durability.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncIterator

from app.config import Settings

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def open_checkpointer(settings: Settings) -> AsyncIterator[object]:
    if settings.has_postgres:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            async with AsyncPostgresSaver.from_conn_string(settings.database_url) as saver:
                await saver.setup()  # idempotent: creates checkpoint tables if absent
                logger.info("Using Postgres checkpointer")
                yield saver
                return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Postgres checkpointer unavailable (%s); falling back to memory", exc)

    from langgraph.checkpoint.memory import MemorySaver

    logger.info("Using in-memory checkpointer (no crash recovery)")
    yield MemorySaver()
