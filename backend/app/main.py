"""FastAPI backend: REST endpoints + WebSocket agent protocol."""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import db
from . import repository as repo
from . import tools
from .agent import AgentRunner
from .config import has_api_key, settings, venv_python
from .schemas import (
    AppSettings,
    ApprovalRequest,
    CreateProjectRequest,
    CreateProjectResponse,
    ModelUpdate,
    PermissionModeUpdate,
    ProjectPathUpdate,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await db.init_db()
    yield
    await db.close_db()


app = FastAPI(title="RND CB Agent Backend", lifespan=lifespan)

# The renderer runs as a local Electron/Vite origin; allow local access.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

runner = AgentRunner()


def _app_settings() -> AppSettings:
    return AppSettings(
        projectPath=settings.project_path,
        model=settings.model,
        permissionMode=settings.permission_mode,  # type: ignore[arg-type]
        hasApiKey=has_api_key(),
        dbConnected=db.is_connected(),
    )


# ---------------------- REST ----------------------
@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/settings", response_model=AppSettings)
async def get_settings() -> AppSettings:
    return _app_settings()


@app.post("/api/settings/model", response_model=AppSettings)
async def set_model(body: ModelUpdate) -> AppSettings:
    settings.model = body.model
    return _app_settings()


@app.post("/api/settings/permission-mode", response_model=AppSettings)
async def set_permission_mode(body: PermissionModeUpdate) -> AppSettings:
    settings.permission_mode = body.mode
    return _app_settings()


@app.post("/api/settings/project-path", response_model=AppSettings)
async def set_project_path(body: ProjectPathUpdate) -> AppSettings:
    if body.path and os.path.isdir(body.path):
        settings.project_path = body.path
    return _app_settings()


@app.post("/api/projects/create", response_model=CreateProjectResponse)
async def create_project(body: CreateProjectRequest) -> CreateProjectResponse:
    parent = os.path.abspath(os.path.expanduser(body.parentPath.strip()))
    name = body.name.strip()

    if not name or any(sep in name for sep in ("/", "\\")) or name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid project name.")
    if not os.path.isdir(parent):
        raise HTTPException(status_code=400, detail=f"Parent directory does not exist: {parent}")

    target = os.path.join(parent, name)
    if os.path.exists(target):
        raise HTTPException(status_code=400, detail=f"A file or folder named '{name}' already exists here.")

    try:
        os.makedirs(target)
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Could not create project directory: {exc}")

    venv_created = False
    venv_message = ""
    if body.createVenv:
        py = venv_python()
        try:
            proc = await asyncio.create_subprocess_exec(
                py,
                "-m",
                "venv",
                ".venv",
                cwd=target,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
            output = stdout.decode("utf-8", errors="replace").strip() if stdout else ""
            if proc.returncode == 0:
                venv_created = True
                venv_message = f"Virtual environment created at .venv using {py}."
            else:
                venv_message = f"venv creation failed (exit {proc.returncode}): {output or 'no output'}"
        except FileNotFoundError:
            venv_message = f"'{py}' not found. Set VENV_PYTHON to a valid Python interpreter."
        except asyncio.TimeoutError:
            venv_message = "venv creation timed out."

    # Make the new project the active one.
    settings.project_path = target

    return CreateProjectResponse(
        settings=_app_settings(),
        projectPath=target,
        venvCreated=venv_created,
        venvMessage=venv_message,
    )


@app.get("/api/files")
async def list_files(path: str = ".") -> list:
    """List the immediate children of a directory inside the project root."""
    root = settings.project_path or "."
    try:
        return tools.list_dir(root, path)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/file")
async def read_file(path: str) -> dict:
    """Read a file's content for the viewer."""
    root = settings.project_path or "."
    try:
        content = tools.read_file(root, path)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"path": path, "content": content}


@app.get("/api/conversations")
async def list_conversations() -> list:
    return [c.model_dump() for c in await repo.list_conversations()]


@app.get("/api/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str) -> list:
    return [m.model_dump() for m in await repo.get_messages(conversation_id)]


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str) -> dict:
    await repo.delete_conversation(conversation_id)
    return {"ok": True}


# ---------------------- WebSocket ----------------------
@app.websocket("/ws/agent")
async def agent_ws(ws: WebSocket) -> None:
    await ws.accept()

    pending_approvals: dict[str, asyncio.Future[bool]] = {}
    cancelled: set[str] = set()
    tasks: set[asyncio.Task] = set()
    send_lock = asyncio.Lock()

    async def emit(event: dict) -> None:
        async with send_lock:
            await ws.send_json(event)

    async def request_approval(req: ApprovalRequest) -> bool:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[bool] = loop.create_future()
        pending_approvals[req.id] = fut
        await emit({"type": "approval_request", **req.model_dump()})
        try:
            return await fut
        finally:
            pending_approvals.pop(req.id, None)

    async def start_run(conversation_id: str | None, prompt: str) -> None:
        if not conversation_id:
            conv = await repo.create_conversation(settings.project_path)
            conversation_id = conv.id
            await emit({"type": "conversation_created", "conversation": conv.model_dump()})
        await repo.add_message(conversation_id, "user", prompt)
        cancelled.discard(conversation_id)

        cid = conversation_id
        task = asyncio.create_task(
            runner.run(cid, emit, request_approval, lambda: cid in cancelled)
        )
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")
            if msg_type == "run":
                await start_run(data.get("conversationId"), data.get("prompt", ""))
            elif msg_type == "approval":
                fut = pending_approvals.get(data.get("id"))
                if fut and not fut.done():
                    fut.set_result(bool(data.get("approved")))
            elif msg_type == "cancel":
                cid = data.get("conversationId")
                if cid:
                    cancelled.add(cid)
    except WebSocketDisconnect:
        pass
    finally:
        for task in tasks:
            task.cancel()
        for fut in pending_approvals.values():
            if not fut.done():
                fut.set_result(False)
