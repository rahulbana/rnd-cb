"""FastAPI backend: serves the frontend and exposes chat + direct tool APIs."""
from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent.orchestrator import get_agent
from .config import config
from .storage.db import init_db
from .tools import build_registry

app = FastAPI(title="AI Agent", version="1.0.0")


@app.on_event("startup")
def _startup() -> None:
    init_db()
    get_agent()  # build the registry once at startup


# ---------------------------- request models ----------------------------

class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class ToolRequest(BaseModel):
    arguments: dict = {}


# ------------------------------- API routes -----------------------------

@app.get("/api/status")
def status() -> dict:
    return {
        "ok": True,
        "llm_configured": config.has_openai(),
        "model": config.OPENAI_MODEL if config.has_openai() else None,
        "tool_count": len(build_registry()),
    }


@app.get("/api/tools")
def list_tools() -> dict:
    """Return tool metadata grouped by category (for the UI sidebar)."""
    registry = build_registry()
    grouped: dict[str, list] = {}
    for tool in registry.values():
        grouped.setdefault(tool.category, []).append({
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        })
    return {"ok": True, "categories": grouped, "count": len(registry)}


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    agent = get_agent()
    result = agent.chat([m.model_dump() for m in req.messages])
    return result


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    """Stream the agent's turn as Server-Sent Events (one JSON object per event)."""
    agent = get_agent()
    messages = [m.model_dump() for m in req.messages]

    def event_source():
        try:
            for event in agent.chat_stream(messages):
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except Exception as exc:  # surface unexpected failures to the client
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/tool/{name}")
def run_tool(name: str, req: ToolRequest) -> JSONResponse:
    """Directly invoke a single tool (used by the UI's tool panels)."""
    registry = build_registry()
    tool = registry.get(name)
    if tool is None:
        return JSONResponse(status_code=404,
                            content={"ok": False, "error": f"Unknown tool '{name}'."})
    try:
        result = tool.run(**req.arguments)
    except Exception as exc:
        result = {"ok": False, "error": f"Tool '{name}' failed: {exc}"}
    return JSONResponse(content=result)


# ------------------------------ static frontend -------------------------

@app.get("/")
def index() -> FileResponse:
    return FileResponse(config.FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=config.FRONTEND_DIR), name="static")
