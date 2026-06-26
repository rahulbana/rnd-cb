"""Async event bus used to stream agent progress to the client.

Agent nodes push structured events onto an ``asyncio.Queue``; the API layer
drains the queue and forwards each event to the browser over SSE.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

from ..schemas.events import EventType

# Sentinel pushed onto the queue when a run is complete.
DONE = object()


class EventBus:
    def __init__(self) -> None:
        self.queue: "asyncio.Queue[Any]" = asyncio.Queue()

    async def emit(self, type: EventType | str, **data: Any) -> None:
        event: Dict[str, Any] = {
            "type": type.value if isinstance(type, EventType) else type,
            "ts": time.time(),
            **data,
        }
        await self.queue.put(event)

    async def close(self) -> None:
        await self.queue.put(DONE)


def get_event_bus(config: Optional[dict]) -> Optional[EventBus]:
    """Pull the event bus out of a LangGraph RunnableConfig (if present)."""
    if not config:
        return None
    return config.get("configurable", {}).get("event_bus")
