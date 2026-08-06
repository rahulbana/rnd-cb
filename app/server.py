"""FastAPI backend: serves the frontend and exposes chat + direct tool APIs."""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent.orchestrator import get_agent
from .config import config
from .logging_config import get_logger, setup_logging
from .storage import db
from .storage.db import init_db
from .tools import build_registry

setup_logging()
logger = get_logger("server")

app = FastAPI(title="AI Agent", version="1.0.0")


@app.on_event("startup")
def _startup() -> None:
    setup_logging()
    init_db()
    get_agent()  # build the registry once at startup
    logger.info("Server started on %s", config.base_url)


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log any uncaught exception raised while handling a request."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": f"Internal server error: {exc}"},
    )


# ---------------------------- request models ----------------------------

class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    conversation_id: int | None = None


class ToolRequest(BaseModel):
    arguments: dict = {}


class OpenRequest(BaseModel):
    path: str
    reveal: bool = False


class SettingsRequest(BaseModel):
    provider: str | None = None
    model: str | None = None


class NewConversation(BaseModel):
    title: str | None = None


class RenameConversation(BaseModel):
    title: str


# ------------------------------- API routes -----------------------------

@app.get("/api/status")
def status() -> dict:
    return {
        "ok": True,
        "llm_configured": config.llm_configured(),
        "provider": config.active_provider(),
        "model": config.active_model() if config.llm_configured() else None,
        "tool_count": len(build_registry()),
    }


@app.get("/api/settings")
def get_settings() -> dict:
    return {
        "ok": True,
        "provider": config.active_provider(),
        "model": config.active_model(),
        "providers": ["openai", "ollama"],
        "openai_key_set": bool(config.OPENAI_API_KEY),
        "models": {"openai": config._models["openai"], "ollama": config._models["ollama"]},
        "ollama_base_url": config.OLLAMA_BASE_URL,
    }


@app.post("/api/settings")
def update_settings(req: SettingsRequest) -> dict:
    from .agent.client import reset_client_cache

    config.set_llm(req.provider, req.model)
    reset_client_cache()
    logger.info("LLM provider set to %s (model=%s)",
                config.active_provider(), config.active_model())
    return {
        "ok": True,
        "provider": config.active_provider(),
        "model": config.active_model(),
        "configured": config.llm_configured(),
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
    """Stream the agent's turn as Server-Sent Events (one JSON object per event).

    When a `conversation_id` is supplied, the latest user message is persisted
    before streaming and the assembled assistant reply is persisted on
    completion, so the conversation survives restarts.
    """
    agent = get_agent()
    messages = [m.model_dump() for m in req.messages]
    conv_id = req.conversation_id

    # Persist the newest user turn up-front (the client sends full history).
    if conv_id and messages and messages[-1]["role"] == "user":
        db.add_message(conv_id, "user", messages[-1]["content"])

    def event_source():
        assistant_parts: list[str] = []
        try:
            for event in agent.chat_stream(messages):
                if event.get("type") == "token":
                    assistant_parts.append(event["text"])
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except Exception as exc:  # surface unexpected failures to the client
            logger.exception("Error while streaming chat response")
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        finally:
            if conv_id and assistant_parts:
                db.add_message(conv_id, "assistant", "".join(assistant_parts))

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------- conversations -----------------------------

@app.get("/api/conversations")
def list_conversations() -> dict:
    return {"ok": True, "conversations": db.list_conversations()}


@app.post("/api/conversations")
def create_conversation(req: NewConversation) -> dict:
    conv = db.create_conversation(req.title or "New chat")
    return {"ok": True, "conversation": conv}


@app.get("/api/conversations/{conv_id}")
def get_conversation(conv_id: int) -> JSONResponse:
    conv = db.get_conversation(conv_id)
    if conv is None:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Not found."})
    return JSONResponse(content={"ok": True, "conversation": conv,
                                 "messages": db.get_messages(conv_id)})


@app.patch("/api/conversations/{conv_id}")
def rename_conversation(conv_id: int, req: RenameConversation) -> JSONResponse:
    if not db.rename_conversation(conv_id, req.title):
        return JSONResponse(status_code=404, content={"ok": False, "error": "Not found."})
    return JSONResponse(content={"ok": True})


@app.delete("/api/conversations/{conv_id}")
def delete_conversation(conv_id: int) -> JSONResponse:
    if not db.delete_conversation(conv_id):
        return JSONResponse(status_code=404, content={"ok": False, "error": "Not found."})
    return JSONResponse(content={"ok": True})


@app.post("/api/tool/{name}")
def run_tool(name: str, req: ToolRequest) -> JSONResponse:
    """Directly invoke a single tool (used by the UI's tool panels)."""
    registry = build_registry()
    tool = registry.get(name)
    if tool is None:
        logger.warning("Direct call to unknown tool '%s'", name)
        return JSONResponse(status_code=404,
                            content={"ok": False, "error": f"Unknown tool '{name}'."})
    try:
        logger.info("Direct tool call: %s(%s)", name, req.arguments)
        result = tool.run(**req.arguments)
    except Exception as exc:
        logger.exception("Direct tool '%s' raised an exception", name)
        result = {"ok": False, "error": f"Tool '{name}' failed: {exc}"}
    if isinstance(result, dict) and not result.get("ok", True):
        logger.error("Direct tool '%s' returned an error: %s", name, result.get("error"))
    return JSONResponse(content=result)


@app.post("/api/upload")
def upload_file(file: UploadFile = File(...)) -> JSONResponse:
    """Accept an uploaded file, store it under UPLOAD_DIR, and return its path."""
    original = file.filename or "upload"
    safe = re.sub(r"[^\w.\-]", "_", original)[-80:] or "upload"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = config.UPLOAD_DIR / f"{stamp}_{safe}"
    try:
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    except Exception as exc:
        logger.exception("Upload failed for %s", original)
        return JSONResponse(status_code=500,
                            content={"ok": False, "error": f"Upload failed: {exc}"})
    finally:
        file.file.close()

    size = dest.stat().st_size
    logger.info("Uploaded %s (%d bytes) -> %s", original, size, dest)
    return JSONResponse(content={
        "ok": True,
        "path": str(dest),
        "filename": original,
        "content_type": file.content_type,
        "bytes": size,
    })


@app.post("/api/open")
def open_path(req: OpenRequest) -> JSONResponse:
    """Open a file with its default app, or reveal it in the OS file manager."""
    from .desktop import OpenError, open_target
    try:
        target = open_target(req.path, req.reveal)
        return JSONResponse(content={"ok": True, "path": str(target)})
    except FileNotFoundError:
        return JSONResponse(status_code=404,
                            content={"ok": False, "error": f"Path not found: {req.path}"})
    except OpenError as exc:
        logger.error("Could not open %s: %s", req.path, exc)
        return JSONResponse(status_code=500,
                            content={"ok": False, "error": str(exc)})
    except Exception as exc:
        logger.exception("Failed to open path: %s", req.path)
        return JSONResponse(status_code=500,
                            content={"ok": False, "error": f"Could not open: {exc}"})


# ------------------------------ static frontend -------------------------

@app.get("/")
def index() -> FileResponse:
    return FileResponse(config.FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=config.FRONTEND_DIR), name="static")
