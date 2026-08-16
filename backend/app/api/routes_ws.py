"""WebSocket endpoints for streaming ingestion progress and chat responses."""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..agent.agent import run_agent
from ..config import get_settings
from ..core.events import EventType, bus
from ..core.logging import get_logger
from ..rag.pipeline import ChatOptions, run_chat
from ..services.ingest_service import ingest
from .routes_documents import PENDING_JOBS

router = APIRouter(tags=["ws"])
log = get_logger(__name__)


async def _relay(ws: WebSocket, channel: str, task_factory) -> None:
    """Subscribe to a channel FIRST, then start the producing task, then relay
    every event to the client until DONE/ERROR. Subscribing before starting the
    task guarantees no early events are dropped."""
    queue = bus.subscribe(channel)
    task = asyncio.create_task(task_factory())
    try:
        while True:
            event = await queue.get()
            if event is None:
                break
            await ws.send_json(event.json_dict())
            if event.type in (EventType.DONE, EventType.ERROR):
                break
    except WebSocketDisconnect:
        log.info("Client disconnected from %s", channel)
    finally:
        bus.unsubscribe(channel, queue)
        if not task.done():
            # Let the producer finish/cleanup; it also closes the channel.
            try:
                await asyncio.wait_for(task, timeout=5)
            except (asyncio.TimeoutError, Exception):  # noqa: BLE001
                task.cancel()


@router.websocket("/ws/ingest/{job_id}")
async def ws_ingest(ws: WebSocket, job_id: str) -> None:
    await ws.accept()
    job = PENDING_JOBS.pop(job_id, None)
    if job is None:
        await ws.send_json({"type": "error", "detail": "Unknown or already-started job."})
        await ws.close()
        return
    channel = f"ingest:{job_id}"
    await _relay(
        ws, channel,
        lambda: ingest(channel, path=job.path, source_name=job.source_name,
                       raw_text=job.raw_text),
    )
    await ws.close()


@router.websocket("/ws/chat")
async def ws_chat(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            payload = await ws.receive_json()
            query = (payload.get("query") or "").strip()
            if not query:
                await ws.send_json({"type": "error", "detail": "Empty query."})
                continue
            options = ChatOptions.from_dict(payload.get("options"))
            settings = get_settings()
            agent_on = settings.agent_enabled if options.agent_enabled is None \
                else options.agent_enabled
            runner = run_agent if agent_on else run_chat
            channel = f"chat:{uuid.uuid4().hex}"
            await _relay(ws, channel, lambda q=query, o=options, r=runner:
                         r(channel, q, o))
    except WebSocketDisconnect:
        log.info("Chat socket disconnected")
