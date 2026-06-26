"""Orchestrates an agent run and exposes it as a stream of progress events."""
from __future__ import annotations

import asyncio
import time
from typing import AsyncGenerator, Dict

from ..agent.graph import get_graph
from ..core.config import Settings
from ..core.exceptions import AppError
from ..core.logging import get_logger
from ..observability.metrics import (
    AGENT_RUN_DURATION,
    AGENT_RUNS,
    AGENT_RUNS_IN_PROGRESS,
    AGENT_SOURCES,
)
from ..schemas.events import EventType
from .event_bus import DONE, EventBus

logger = get_logger(__name__)


class SearchService:
    """Runs the deep-search agent and yields events for streaming transports."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._graph = get_graph()

    async def _run(self, bus: EventBus, query: str, num_subqueries: int) -> None:
        start = time.perf_counter()
        AGENT_RUNS.labels(status="started").inc()
        AGENT_RUNS_IN_PROGRESS.inc()
        try:
            await bus.emit(EventType.RUN_START, query=query)
            result = await self._graph.ainvoke(
                {"query": query, "num_subqueries": num_subqueries},
                config={"configurable": {"event_bus": bus}},
            )

            duration = time.perf_counter() - start
            stats = self._summarize(result, duration)
            AGENT_RUN_DURATION.observe(duration)
            AGENT_SOURCES.observe(stats["sources"])
            AGENT_RUNS.labels(status="completed").inc()
            logger.info(
                "Run completed in %.2fs | subqueries=%d sources=%d report_chars=%d",
                duration, stats["subqueries"], stats["sources"], stats["report_chars"],
            )
            await bus.emit(EventType.STATS, **stats)
            await bus.emit(EventType.DONE)
        except AppError as exc:
            AGENT_RUNS.labels(status="failed").inc()
            logger.error("Agent run failed: %s", exc)
            await bus.emit(EventType.ERROR, error=exc.message)
        except Exception as exc:  # noqa: BLE001 - last-resort safety net
            AGENT_RUNS.labels(status="failed").inc()
            logger.exception("Unexpected error during agent run")
            await bus.emit(EventType.ERROR, error=str(exc))
        finally:
            AGENT_RUNS_IN_PROGRESS.dec()
            await bus.close()

    @staticmethod
    def _summarize(result: dict, duration: float) -> Dict:
        report = result.get("report", "") or ""
        return {
            "duration_ms": round(duration * 1000),
            "subqueries": len(result.get("subqueries", []) or []),
            "sources": len(result.get("sources", []) or []),
            "report_chars": len(report),
        }

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
