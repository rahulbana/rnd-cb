"""HTTP API routes."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import run_pipeline
from app.config import settings
from app.database import SessionLocal, get_db
from app.schemas import GenerateRequest
from app.services import content_service

router = APIRouter(prefix="/api", tags=["content"])


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "openai_configured": settings.has_openai,
        "deep_search_configured": settings.has_tavily,
    }


@router.post("/generate/stream")
async def generate_stream(req: GenerateRequest):
    """Stream the multi-agent pipeline as newline-delimited JSON (NDJSON).

    On 'complete', the result is persisted and the saved record (with id) is emitted.
    """

    async def event_generator():
        final_result: dict | None = None
        async for event in run_pipeline(req):
            if event.get("type") == "complete":
                final_result = event.get("result")
            yield json.dumps(event) + "\n"

        if final_result is not None:
            async with SessionLocal() as db:
                piece = await content_service.save_content(db, req, final_result)
                yield json.dumps({"type": "saved", "content": piece.to_dict()}) + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/generate")
async def generate(req: GenerateRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """Non-streaming generation: runs the full pipeline and returns the saved record."""
    final_result: dict | None = None
    error: str | None = None
    async for event in run_pipeline(req):
        if event.get("type") == "complete":
            final_result = event.get("result")
        elif event.get("type") == "error":
            error = event.get("message")

    if error or final_result is None:
        raise HTTPException(status_code=502, detail=error or "Generation failed")

    piece = await content_service.save_content(db, req, final_result)
    return piece.to_dict()


@router.get("/content")
async def list_content(db: AsyncSession = Depends(get_db)) -> list[dict]:
    pieces = await content_service.list_content(db)
    return [p.to_dict() for p in pieces]


@router.get("/content/{content_id}")
async def get_content(content_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    piece = await content_service.get_content(db, content_id)
    if piece is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return piece.to_dict()
