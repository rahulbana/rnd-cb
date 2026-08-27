"""In-process pub/sub for streaming run progress to SSE subscribers.

Each research run has an event history (for replay to late subscribers) and a
set of live subscriber queues. This is intentionally in-memory and therefore
single-process: the durable source of truth is the Postgres checkpointer, so a
dropped stream never loses results — a client can re-read final state via the
REST endpoint. For multi-worker horizontal scaling, swap this for Redis
pub/sub (same interface).
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import AsyncIterator

logger = logging.getLogger(__name__)

# Cap retained events per run to bound memory for very long runs.
_MAX_HISTORY = 500


class EventBroker:
    def __init__(self) -> None:
        self._history: dict[str, list[dict]] = defaultdict(list)
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._terminated: set[str] = set()

    def publish(self, thread_id: str, event: dict) -> None:
        history = self._history[thread_id]
        history.append(event)
        if len(history) > _MAX_HISTORY:
            # Keep the first event (run_started) plus the most recent tail.
            self._history[thread_id] = history[:1] + history[-(_MAX_HISTORY - 1):]
        if event.get("terminal"):
            self._terminated.add(thread_id)
        for queue in list(self._subscribers.get(thread_id, ())):
            queue.put_nowait(event)

    async def subscribe(self, thread_id: str) -> AsyncIterator[dict]:
        """Yield historical events, then live ones until a terminal event."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[thread_id].add(queue)
        try:
            # Replay history so a late subscriber catches up.
            for event in list(self._history.get(thread_id, ())):
                yield event
            if thread_id in self._terminated:
                return
            while True:
                event = await queue.get()
                yield event
                if event.get("terminal"):
                    return
        finally:
            self._subscribers[thread_id].discard(queue)

    def is_terminated(self, thread_id: str) -> bool:
        return thread_id in self._terminated
