"""REST + WebSocket routes."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from ..config import get_settings
from ..llm import build_provider
from ..schemas import CreateProjectRequest, SimpleOk
from ..services import bus, run_manager
from ..services import project_service as svc

router = APIRouter()


@router.get("/api/config")
async def get_config() -> dict:
    settings = get_settings()
    provider_name = settings.llm_provider
    model = (
        settings.openai_model
        if provider_name == "openai"
        else settings.ollama_model
    )
    healthy = None
    try:
        healthy = await build_provider(settings).health()
    except Exception:
        healthy = False
    return {
        "provider": provider_name,
        "model": model,
        "memory_enabled": settings.memory_enabled,
        "workspace_root": str(settings.workspace_root_path),
        "healthy": healthy,
    }


@router.post("/api/projects")
async def create_project(req: CreateProjectRequest) -> dict:
    project = svc.create_project(req.goal, req.name)
    if req.auto_start:
        run_manager.start(project["id"])
    return project


@router.get("/api/projects")
async def list_projects() -> list[dict]:
    projects = svc.list_projects()
    for p in projects:
        p["running"] = run_manager.is_running(p["id"])
    return projects


@router.get("/api/projects/{project_id}")
async def get_project(project_id: str) -> dict:
    project = svc.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    project["running"] = run_manager.is_running(project_id)
    project["artifacts"] = svc.get_artifacts(project_id)
    project["messages"] = svc.get_messages(project_id)
    return project


@router.get("/api/projects/{project_id}/events")
async def get_events(project_id: str, after: int = Query(0, ge=0)) -> list[dict]:
    if not svc.get_project(project_id):
        raise HTTPException(404, "Project not found")
    return svc.get_events(project_id, after_seq=after)


@router.get("/api/projects/{project_id}/files")
async def get_file(project_id: str, path: str = Query(...)) -> dict:
    content = svc.get_file_content(project_id, path)
    if content is None:
        raise HTTPException(404, "File not found")
    return {"path": path, "content": content}


@router.post("/api/projects/{project_id}/run")
async def run_project(project_id: str) -> SimpleOk:
    if not svc.get_project(project_id):
        raise HTTPException(404, "Project not found")
    started = run_manager.start(project_id)
    return SimpleOk(ok=started, detail="started" if started else "already running")


@router.post("/api/projects/{project_id}/stop")
async def stop_project(project_id: str) -> SimpleOk:
    stopped = await run_manager.stop(project_id)
    return SimpleOk(ok=stopped, detail="stopping" if stopped else "not running")


@router.delete("/api/projects/{project_id}")
async def delete_project(project_id: str) -> SimpleOk:
    await run_manager.stop(project_id)
    ok = svc.delete_project(project_id)
    if not ok:
        raise HTTPException(404, "Project not found")
    return SimpleOk(ok=True, detail="deleted")


@router.websocket("/ws/projects/{project_id}")
async def project_stream(websocket: WebSocket, project_id: str) -> None:
    """Stream events for a project.

    On connect we replay the persisted backlog (so a reopened UI catches up),
    then forward live events. The client may send {"after": <seq>} to control
    where the replay starts.
    """
    await websocket.accept()

    if not svc.get_project(project_id):
        await websocket.send_json({"type": "error", "message": "Project not found"})
        await websocket.close()
        return

    after = 0
    try:
        # Optional first message telling us the last seq the client already has.
        try:
            init = await asyncio.wait_for(websocket.receive_json(), timeout=0.25)
            after = int(init.get("after", 0))
        except (asyncio.TimeoutError, Exception):
            after = 0

        # Replay backlog.
        for event in svc.get_events(project_id, after_seq=after):
            await websocket.send_json(event)

        # Subscribe to live events.
        queue = await bus.subscribe(project_id)
        try:
            while True:
                event = await queue.get()
                await websocket.send_json(event)
        finally:
            await bus.unsubscribe(project_id, queue)
    except WebSocketDisconnect:
        pass
    except Exception:
        # Client vanished or send failed; just close quietly.
        try:
            await websocket.close()
        except Exception:
            pass
