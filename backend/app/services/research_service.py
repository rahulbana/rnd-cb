"""Orchestrates research runs: starts them in the background, streams progress,
and exposes durable state lookups.

A run is identified by a LangGraph ``thread_id``. Because state is checkpointed
to Postgres, a run's result is retrievable even after the streaming connection
(or the whole process) goes away — start it, then reconnect to stream or poll.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from langgraph.checkpoint.base import BaseCheckpointSaver

from app.agent.graph import build_graph
from app.core.config import Settings
from app.services.events import EventBroker

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResearchService:
    def __init__(self, checkpointer: BaseCheckpointSaver, settings: Settings) -> None:
        self._graph = build_graph(checkpointer)
        self._settings = settings
        self._broker = EventBroker()
        self._tasks: dict[str, asyncio.Task] = {}

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def start_research(self, topic: str) -> str:
        thread_id = uuid.uuid4().hex
        task = asyncio.create_task(self._run(thread_id, topic))
        self._tasks[thread_id] = task
        task.add_done_callback(lambda t: self._tasks.pop(thread_id, None))
        logger.info("research run started", extra={"thread_id": thread_id, "topic": topic})
        return thread_id

    async def _run(self, thread_id: str, topic: str) -> None:
        config = {"configurable": {"thread_id": thread_id}}
        initial: dict[str, Any] = {
            "topic": topic,
            "max_iterations": self._settings.max_iterations,
            "max_queries_per_iteration": self._settings.max_queries_per_iteration,
        }
        self._broker.publish(
            thread_id,
            {"type": "run_started", "topic": topic, "ts": _now(), "terminal": False},
        )
        try:
            async for chunk in self._graph.astream(initial, config, stream_mode="updates"):
                for node_name, update in chunk.items():
                    event = self._to_event(node_name, update)
                    if event:
                        event["ts"] = _now()
                        self._broker.publish(thread_id, event)

            final = await self.get_state(thread_id)
            self._broker.publish(
                thread_id,
                {
                    "type": "completed",
                    "ts": _now(),
                    "terminal": True,
                    "final_report": (final or {}).get("final_report", ""),
                    "sources": (final or {}).get("sources", []),
                },
            )
            logger.info("research run completed", extra={"thread_id": thread_id})
        except asyncio.CancelledError:
            self._broker.publish(
                thread_id, {"type": "cancelled", "ts": _now(), "terminal": True}
            )
            logger.warning("research run cancelled", extra={"thread_id": thread_id})
            raise
        except Exception as exc:  # noqa: BLE001 - report and terminate the stream cleanly
            self._broker.publish(
                thread_id,
                {"type": "error", "ts": _now(), "terminal": True, "message": str(exc)},
            )
            logger.exception("research run failed", extra={"thread_id": thread_id})

    def cancel(self, thread_id: str) -> bool:
        task = self._tasks.get(thread_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    # ------------------------------------------------------------------ #
    # Streaming / state
    # ------------------------------------------------------------------ #
    async def subscribe(self, thread_id: str) -> AsyncIterator[dict]:
        async for event in self._broker.subscribe(thread_id):
            yield event

    async def get_state(self, thread_id: str) -> dict[str, Any] | None:
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = await self._graph.aget_state(config)
        if not snapshot or not snapshot.values:
            return None
        return dict(snapshot.values)

    def is_running(self, thread_id: str) -> bool:
        task = self._tasks.get(thread_id)
        return bool(task and not task.done())

    async def shutdown(self) -> None:
        for task in list(self._tasks.values()):
            task.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)

    # ------------------------------------------------------------------ #
    # Node update -> client event mapping
    # ------------------------------------------------------------------ #
    @staticmethod
    def _to_event(node_name: str, update: dict | None) -> dict | None:
        update = update or {}
        if node_name == "plan":
            return {
                "type": "planned",
                "phase": "planning",
                "plan": update.get("plan", []),
                "queries": update.get("pending_queries", []),
            }
        if node_name == "search":
            return {
                "type": "searched",
                "phase": "searching",
                "queries": update.get("executed_queries", []),
                "new_sources": len(update.get("sources", []) or []),
                "new_findings": len(update.get("findings", []) or []),
            }
        if node_name == "reflect":
            return {
                "type": "reflected",
                "phase": "reflecting",
                "iteration": update.get("iteration", 0),
                "is_complete": update.get("is_complete", False),
                "knowledge_gaps": update.get("knowledge_gaps", []),
                "next_queries": update.get("pending_queries", []),
            }
        if node_name == "synthesize":
            return {"type": "synthesized", "phase": "synthesizing"}
        return None
