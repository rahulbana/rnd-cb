"""Streaming event schema and an in-memory pub/sub bus.

The pipeline emits fine-grained progress events (parse -> chunk -> embed ->
index for ingestion; embed_query -> retrieve -> rerank -> generate for chat).
WebSocket handlers subscribe to a channel and relay these events to the client
so the frontend can render each step as it happens.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from enum import Enum
from typing import Any, AsyncIterator

from pydantic import BaseModel, Field


class Phase(str, Enum):
    INGEST = "ingest"
    CHAT = "chat"


class Status(str, Enum):
    START = "start"
    PROGRESS = "progress"
    DONE = "done"
    ERROR = "error"


class EventType(str, Enum):
    STEP = "step"      # a pipeline step changed status
    TOKEN = "token"    # a chunk of streamed LLM output
    SOURCES = "sources"  # the retrieved passages used as context
    DONE = "done"      # the stream is complete
    ERROR = "error"    # a fatal error terminated the stream


class Event(BaseModel):
    type: EventType
    phase: Phase | None = None
    step: str | None = None
    status: Status | None = None
    detail: str | None = None
    data: Any | None = None

    def json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


# Canonical step identifiers (kept in sync with the frontend timeline).
INGEST_STEPS = ["upload", "parse", "chunk", "embed", "index", "complete"]
CHAT_STEPS = ["embed_query", "retrieve", "rerank", "generate", "complete"]


class EventBus:
    """Fan-in/fan-out of events over named channels backed by asyncio queues.

    A background ingestion job (or a chat request) publishes onto a channel;
    a WebSocket connection drains it. ``None`` is the sentinel that closes a
    subscriber's stream.
    """

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, channel: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[channel].append(queue)
        return queue

    def unsubscribe(self, channel: str, queue: asyncio.Queue) -> None:
        subs = self._queues.get(channel)
        if subs and queue in subs:
            subs.remove(queue)
        if subs is not None and not subs:
            self._queues.pop(channel, None)

    async def publish(self, channel: str, event: Event) -> None:
        for queue in list(self._queues.get(channel, [])):
            await queue.put(event)

    async def close(self, channel: str) -> None:
        for queue in list(self._queues.get(channel, [])):
            await queue.put(None)

    async def stream(self, channel: str) -> AsyncIterator[Event]:
        queue = self.subscribe(channel)
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            self.unsubscribe(channel, queue)


# Process-wide singleton. For multi-worker deployments this would be swapped
# for a Redis/NATS-backed implementation behind the same interface.
bus = EventBus()


class StepEmitter:
    """Convenience wrapper to emit consistently-shaped step events.

    Usage::

        async with emitter.step("parse", "Extracting text") as ctx:
            ...
            ctx.detail = "extracted 12 pages"
    """

    def __init__(self, channel: str, phase: Phase) -> None:
        self.channel = channel
        self.phase = phase

    async def emit(self, event: Event) -> None:
        await bus.publish(self.channel, event)

    async def step_start(self, step: str, detail: str | None = None) -> None:
        await self.emit(Event(type=EventType.STEP, phase=self.phase, step=step,
                              status=Status.START, detail=detail))

    async def step_done(self, step: str, detail: str | None = None,
                        data: Any | None = None) -> None:
        await self.emit(Event(type=EventType.STEP, phase=self.phase, step=step,
                              status=Status.DONE, detail=detail, data=data))

    async def step_error(self, step: str, detail: str) -> None:
        await self.emit(Event(type=EventType.STEP, phase=self.phase, step=step,
                              status=Status.ERROR, detail=detail))

    async def token(self, text: str) -> None:
        await self.emit(Event(type=EventType.TOKEN, phase=self.phase, data=text))

    async def sources(self, sources: list[dict]) -> None:
        await self.emit(Event(type=EventType.SOURCES, phase=self.phase, data=sources))

    async def done(self) -> None:
        await self.emit(Event(type=EventType.DONE, phase=self.phase))

    async def error(self, detail: str) -> None:
        await self.emit(Event(type=EventType.ERROR, phase=self.phase, detail=detail))
