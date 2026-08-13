"""In-process publish/subscribe for live event streaming.

Each connected client (WebSocket) subscribes to a project and receives an
asyncio queue. Emitting an event pushes it to every live subscriber. Events
are *also* persisted (see :mod:`autodev.services.events`) so a client that
reconnects can replay everything it missed.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, project_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        async with self._lock:
            self._subscribers[project_id].add(queue)
        return queue

    async def unsubscribe(self, project_id: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            self._subscribers[project_id].discard(queue)
            if not self._subscribers[project_id]:
                self._subscribers.pop(project_id, None)

    async def publish(self, project_id: str, event: dict[str, Any]) -> None:
        # Copy to avoid mutation while iterating.
        for queue in list(self._subscribers.get(project_id, ())):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Slow consumer: drop oldest, then enqueue.
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except Exception:
                    pass


# Module-level singleton shared across the app.
bus = EventBus()
