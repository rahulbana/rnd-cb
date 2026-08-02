"""FastAPI application exposing the LangGraph movie assistant over HTTP.

Endpoints
---------
``GET  /api/health``       Liveness plus the discovered tool list.
``POST /api/chat/stream``  Server-Sent Events stream of the assistant's reply,
                           including token deltas and tool-call notifications.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from .agent import Assistant, build_assistant
from .config import get_settings
from .schemas import ChatRequest, HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | backend | %(message)s",
)
logger = logging.getLogger("backend.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the agent once on startup so tools are discovered a single time."""
    settings = get_settings()
    try:
        app.state.assistant = await build_assistant(settings)
        logger.info("Assistant ready with tools: %s", app.state.assistant.tool_names)
    except Exception:  # noqa: BLE001 - surface a clear startup failure
        logger.exception("Failed to initialise the assistant. Is the MCP server running?")
        app.state.assistant = None
    yield


settings = get_settings()
app = FastAPI(title="Movies & Utilities Assistant", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_assistant(request: Request) -> Assistant:
    assistant: Assistant | None = getattr(request.app.state, "assistant", None)
    if assistant is None:
        raise HTTPException(
            status_code=503,
            detail="Assistant is not available. Ensure the MCP server is reachable, "
            "then restart the backend.",
        )
    return assistant


def _to_langchain_messages(payload: ChatRequest) -> list:
    lc_messages: list = []
    for message in payload.messages:
        if message.role == "user":
            lc_messages.append(HumanMessage(content=message.content))
        else:
            lc_messages.append(AIMessage(content=message.content))
    return lc_messages


def _sse(event: str, data: dict) -> str:
    """Format a Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/api/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    assistant: Assistant | None = getattr(request.app.state, "assistant", None)
    if assistant is None:
        return HealthResponse(
            status="degraded",
            model=settings.openai_model,
            mcp_server=settings.mcp_server_url,
            tools=[],
        )
    return HealthResponse(
        status="ok",
        model=settings.openai_model,
        mcp_server=settings.mcp_server_url,
        tools=assistant.tool_names,
    )


async def _stream_agent(assistant: Assistant, payload: ChatRequest) -> AsyncIterator[str]:
    """Yield SSE frames as the agent thinks, calls tools, and emits its answer."""
    messages = _to_langchain_messages(payload)
    yield _sse("start", {"model": assistant.settings.openai_model})

    try:
        # ``messages`` stream mode gives us per-token LLM chunks *and* completed
        # tool messages, which we translate into typed SSE events for the UI.
        async for chunk, metadata in assistant.graph.astream(
            {"messages": messages},
            stream_mode="messages",
        ):
            node = metadata.get("langgraph_node") if isinstance(metadata, dict) else None

            if isinstance(chunk, AIMessageChunk):
                # Announce tool calls as they are decided.
                for tool_call in chunk.tool_calls or []:
                    if tool_call.get("name"):
                        yield _sse("tool_call", {"name": tool_call["name"], "args": tool_call.get("args", {})})
                # Stream visible assistant text (skip empty tool-planning chunks).
                if isinstance(chunk.content, str) and chunk.content and node == "agent":
                    yield _sse("token", {"content": chunk.content})

            elif isinstance(chunk, ToolMessage):
                yield _sse("tool_result", {"name": chunk.name, "status": chunk.status})

        yield _sse("done", {})
    except Exception as exc:  # noqa: BLE001 - stream a clean error to the client
        logger.exception("Error while streaming agent response")
        yield _sse("error", {"message": str(exc)})


@app.post("/api/chat/stream")
async def chat_stream(request: Request, payload: ChatRequest) -> StreamingResponse:
    assistant = _get_assistant(request)
    try:
        payload.latest_user_message()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StreamingResponse(
        _stream_agent(assistant, payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering for live streams
        },
    )
