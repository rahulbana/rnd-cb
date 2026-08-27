"""HTTP + SSE routes for the research agent."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.api.schemas import (
    ResearchRequest,
    ResearchStartResponse,
    ResearchStateResponse,
    SourceOut,
)
from app.services.research_service import ResearchService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["research"])


def _service(request: Request) -> ResearchService:
    service: ResearchService | None = getattr(request.app.state, "research_service", None)
    if service is None:  # pragma: no cover - only if startup failed
        raise HTTPException(status_code=503, detail="Service not ready")
    return service


@router.post("/research", response_model=ResearchStartResponse, status_code=202)
async def start_research(payload: ResearchRequest, request: Request) -> ResearchStartResponse:
    service = _service(request)
    thread_id = service.start_research(payload.topic.strip())
    return ResearchStartResponse(thread_id=thread_id)


@router.get("/research/{thread_id}", response_model=ResearchStateResponse)
async def get_research(thread_id: str, request: Request) -> ResearchStateResponse:
    service = _service(request)
    state = await service.get_state(thread_id)
    if state is None:
        if service.is_running(thread_id):
            return ResearchStateResponse(thread_id=thread_id, status="running")
        raise HTTPException(status_code=404, detail="Research run not found")

    status = "running" if service.is_running(thread_id) else "completed"
    return ResearchStateResponse(
        thread_id=thread_id,
        topic=state.get("topic", ""),
        status=status,
        iteration=state.get("iteration", 0),
        is_complete=state.get("is_complete", False),
        plan=state.get("plan", []),
        findings_count=len(state.get("findings", []) or []),
        sources=[SourceOut(**s) for s in state.get("sources", []) or []],
        final_report=state.get("final_report", ""),
    )


@router.delete("/research/{thread_id}", status_code=202)
async def cancel_research(thread_id: str, request: Request) -> dict[str, str]:
    service = _service(request)
    cancelled = service.cancel(thread_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="No running run with that id")
    return {"thread_id": thread_id, "status": "cancelling"}


@router.get("/research/{thread_id}/stream")
async def stream_research(thread_id: str, request: Request) -> EventSourceResponse:
    """Server-Sent Events stream of run progress.

    Emits historical events first (replay), then live updates until a terminal
    event. Safe to (re)connect at any time while or after the run executes.
    """
    service = _service(request)

    async def event_generator():
        async for event in service.subscribe(thread_id):
            if await request.is_disconnected():
                break
            yield {"event": event.get("type", "message"), "data": json.dumps(event)}

    return EventSourceResponse(event_generator())
