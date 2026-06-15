"""Lightweight async event emitter used to stream agent progress to the client.

Each agent node pushes structured events onto an asyncio.Queue. The FastAPI
SSE endpoint drains the queue and forwards events to the browser, so the
frontend can show *exactly* what the backend is doing in real time (which node
is running, which tool is being called, which sources were found, etc.).
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional


# Sentinel pushed onto the queue when the run is complete.
DONE = object()


class EventEmitter:
    def __init__(self) -> None:
        self.queue: "asyncio.Queue[Any]" = asyncio.Queue()

    async def emit(self, type: str, **data: Any) -> None:
        event: Dict[str, Any] = {
            "type": type,
            "ts": time.time(),
            **data,
        }
        await self.queue.put(event)

    async def close(self) -> None:
        await self.queue.put(DONE)


def get_emitter(config: Optional[dict]) -> Optional[EventEmitter]:
    """Pull the emitter out of a LangGraph RunnableConfig (if present)."""
    if not config:
        return None
    return config.get("configurable", {}).get("emitter")
