"""Orchestrates an agent run, streams progress events, and records run history."""
from __future__ import annotations

import asyncio
import time
import uuid
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
from ..persistence.models import RunRecord, StepEvent
from ..persistence.store import RunStore
from ..schemas.events import EventType
from ..schemas.source import Source
from .event_bus import DONE, EventBus

logger = get_logger(__name__)

# Events captured as discrete "steps" in the run history (token excluded — too noisy).
_STEP_EVENTS = {
    EventType.RUN_START.value,
    EventType.NODE_START.value,
    EventType.NODE_END.value,
    EventType.TOOL_CALL.value,
    EventType.TOOL_RESULT.value,
    EventType.TOOL_ERROR.value,
}


class SearchService:
    """Runs the deep-search agent, yields events, and persists each run."""

    def __init__(self, settings: Settings, store: RunStore) -> None:
        self._settings = settings
        self._store = store
        self._graph = get_graph()

    async def _run(self, bus: EventBus, run_id: str, query: str, n: int) -> None:
        start = time.perf_counter()
        AGENT_RUNS.labels(status="started").inc()
        AGENT_RUNS_IN_PROGRESS.inc()
        try:
            await bus.emit(EventType.RUN_START, run_id=run_id, query=query)
            result = await self._graph.ainvoke(
                {"query": query, "num_subqueries": n},
                config={
                    "configurable": {"event_bus": bus},
                    "run_name": "deep-search",
                    "metadata": {"run_id": run_id, "query": query},
                    "tags": ["deep-search"],
                },
            )

            duration = time.perf_counter() - start
            stats = self._summarize(result, duration)
            AGENT_RUN_DURATION.observe(duration)
            AGENT_SOURCES.observe(stats["sources"])
            AGENT_RUNS.labels(status="completed").inc()
            logger.info(
                "Run %s completed in %.2fs | subqueries=%d sources=%d report_chars=%d",
                run_id, duration, stats["subqueries"], stats["sources"], stats["report_chars"],
            )
            await bus.emit(EventType.STATS, **stats)
            await bus.emit(EventType.DONE)
        except AppError as exc:
            AGENT_RUNS.labels(status="failed").inc()
            logger.error("Agent run %s failed: %s", run_id, exc)
            await bus.emit(EventType.ERROR, error=exc.message)
        except Exception as exc:  # noqa: BLE001 - last-resort safety net
            AGENT_RUNS.labels(status="failed").inc()
            logger.exception("Unexpected error during agent run %s", run_id)
            await bus.emit(EventType.ERROR, error=str(exc))
        finally:
            AGENT_RUNS_IN_PROGRESS.dec()
            await bus.close()

    async def stream(
        self, query: str, num_subqueries: int | None = None
    ) -> AsyncGenerator[Dict, None]:
        """Yield each progress event, recording the full run to the store."""
        n = num_subqueries or self._settings.num_subqueries
        run_id = uuid.uuid4().hex
        record = RunRecord(
            id=run_id, query=query, num_subqueries=n,
            status="running", started_at=time.time(),
        )
        await self._store.save(record)

        bus = EventBus()
        task = asyncio.create_task(self._run(bus, run_id, query, n))
        try:
            while True:
                item = await bus.queue.get()
                if item is DONE:
                    break
                self._absorb(record, item)
                yield item
        finally:
            if not task.done():
                task.cancel()
            if record.status == "running":
                record.status = "cancelled"
                record.finished_at = time.time()
            await self._store.save(record)

    # ---- helpers ----
    @staticmethod
    def _summarize(result: dict, duration: float) -> Dict:
        report = result.get("report", "") or ""
        return {
            "duration_ms": round(duration * 1000),
            "subqueries": len(result.get("subqueries", []) or []),
            "sources": len(result.get("sources", []) or []),
            "report_chars": len(report),
        }

    @staticmethod
    def _absorb(record: RunRecord, ev: dict) -> None:
        """Fold a streamed event into the persisted run record."""
        etype = ev.get("type")

        if etype in _STEP_EVENTS:
            record.steps.append(
                StepEvent(
                    ts=ev.get("ts", time.time()),
                    type=etype,
                    node=ev.get("node"),
                    tool=ev.get("tool"),
                    model=ev.get("model"),
                    query=ev.get("query"),
                    count=ev.get("count"),
                    detail=ev.get("detail"),
                    error=ev.get("error"),
                )
            )

        if etype == EventType.SUBQUERIES.value:
            record.subqueries = ev.get("subqueries", []) or []
        elif etype == EventType.SOURCE.value:
            src = ev.get("source") or {}
            if src.get("url") and not any(s.url == src["url"] for s in record.sources):
                record.sources.append(Source(**src))
        elif etype == EventType.REPORT.value:
            if ev.get("report"):
                record.report = ev["report"]
            if ev.get("sources"):
                record.sources = [Source(**s) for s in ev["sources"]]
        elif etype == EventType.STATS.value:
            record.duration_ms = ev.get("duration_ms")
        elif etype == EventType.ERROR.value:
            record.status = "failed"
            record.error = ev.get("error")
            record.finished_at = time.time()
        elif etype == EventType.DONE.value:
            record.status = "completed"
            record.finished_at = time.time()
