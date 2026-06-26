"""Orchestrates an agent run and exposes it as a stream of progress events."""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Dict

from ..agent.graph import get_graph
from ..core.config import Settings
from ..core.exceptions import AppError
from ..core.logging import get_logger
from ..schemas.events import EventType
from .event_bus import DONE, EventBus

logger = get_logger(__name__)


class SearchService:
    """Runs the deep-search agent and yields events for streaming transports."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._graph = get_graph()

    async def _run(self, bus: EventBus, query: str, num_subqueries: int) -> None:
        try:
            await bus.emit(EventType.RUN_START, query=query)
            await self._graph.ainvoke(
                {"query": query, "num_subqueries": num_subqueries},
                config={"configurable": {"event_bus": bus}},
            )
            await bus.emit(EventType.DONE)
        except AppError as exc:
            logger.error("Agent run failed: %s", exc)
            await bus.emit(EventType.ERROR, error=exc.message)
        except Exception as exc:  # noqa: BLE001 - last-resort safety net
            logger.exception("Unexpected error during agent run")
            await bus.emit(EventType.ERROR, error=str(exc))
        finally:
            await bus.close()

    async def stream(
        self, query: str, num_subqueries: int | None = None
    ) -> AsyncGenerator[Dict, None]:
        """Yield each progress event as a dict until the run completes."""
        n = num_subqueries or self._settings.num_subqueries
        bus = EventBus()
        task = asyncio.create_task(self._run(bus, query, n))
        try:
            while True:
                item = await bus.queue.get()
                if item is DONE:
                    break
                yield item
        finally:
            if not task.done():
                task.cancel()
