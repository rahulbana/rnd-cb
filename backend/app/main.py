"""FastAPI application exposing the deep-search agent over Server-Sent Events.

The /api/search endpoint runs the LangGraph agent and streams every progress
event (node start/end, tool calls, sources found, report tokens) to the browser
so the React frontend can show what's happening on the backend in real time.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .agent.graph import agent_graph
from .config import settings
from .events import DONE, EventEmitter

app = FastAPI(title="Deep Search Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN] if settings.FRONTEND_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str
    num_subqueries: int | None = None


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "model": settings.OPENAI_MODEL,
        "search_provider": "tavily" if settings.TAVILY_API_KEY else "duckduckgo",
        "openai_configured": bool(settings.OPENAI_API_KEY),
    }


def _sse(event: dict) -> str:
    """Format a dict as a Server-Sent Event frame."""
    return f"data: {json.dumps(event)}\n\n"


async def _run_agent(emitter: EventEmitter, query: str, num_subqueries: int) -> None:
    """Drive the LangGraph agent, emitting a final 'done'/'error' event."""
    try:
        await emitter.emit("run_start", query=query)
        await agent_graph.ainvoke(
            {"query": query, "num_subqueries": num_subqueries},
            config={"configurable": {"emitter": emitter}},
        )
        await emitter.emit("done")
    except Exception as exc:  # pragma: no cover - surfaced to the client
        await emitter.emit("error", error=str(exc))
    finally:
        await emitter.close()


async def _event_stream(query: str, num_subqueries: int) -> AsyncGenerator[str, None]:
    emitter = EventEmitter()
    task = asyncio.create_task(_run_agent(emitter, query, num_subqueries))
    try:
        while True:
            item = await emitter.queue.get()
            if item is DONE:
                break
            yield _sse(item)
    finally:
        if not task.done():
            task.cancel()


@app.post("/api/search")
async def search(req: SearchRequest) -> StreamingResponse:
    n = req.num_subqueries or settings.NUM_SUBQUERIES
    return StreamingResponse(
        _event_stream(req.query, n),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
