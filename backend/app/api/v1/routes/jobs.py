"""Ingestion job status routes: polling and Server-Sent Events (SSE)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps_auth import get_current_user
from app.api.v1.schemas import JobOut
from app.db.base import SessionLocal, get_db
from app.db.models import Document, IngestionJob, User

router = APIRouter(prefix="/jobs", tags=["jobs"])

_TERMINAL = {"completed", "failed"}


def _to_out(job: IngestionJob) -> JobOut:
    return JobOut(
        id=job.id,
        document_id=job.document_id,
        stage=job.stage,
        progress=job.progress,
        status=job.status,
        error=job.error,
        retries=job.retries,
    )


def _owned_job(job_id: str, db: Session, user: User) -> IngestionJob:
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    document = db.get(Document, job.document_id)
    if document is None or document.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobOut:
    """Poll a job's current stage/progress/status."""
    return _to_out(_owned_job(job_id, db, user))


@router.get("/document/{document_id}", response_model=list[JobOut])
async def jobs_for_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[JobOut]:
    document = db.get(Document, document_id)
    if document is None or document.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Document not found")
    stmt = select(IngestionJob).where(IngestionJob.document_id == document_id)
    return [_to_out(j) for j in db.execute(stmt).scalars().all()]


async def _event_stream(
    job_id: str, *, poll_interval: float, max_seconds: float
) -> AsyncIterator[str]:
    """Yield SSE progress events until the job reaches a terminal state."""
    elapsed = 0.0
    last_signature: tuple[str, int] | None = None
    while True:
        db = SessionLocal()
        try:
            job = db.get(IngestionJob, job_id)
            if job is None:
                yield f"event: error\ndata: {json.dumps({'error': 'job not found'})}\n\n"
                return
            payload = _to_out(job).model_dump()
            signature = (job.status, job.progress)
            terminal = job.status in _TERMINAL
        finally:
            db.close()

        if signature != last_signature:
            yield f"data: {json.dumps(payload)}\n\n"
            last_signature = signature

        if terminal or elapsed >= max_seconds:
            return
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval


@router.get("/{job_id}/stream")
async def stream_job(
    job_id: str,
    poll_interval: float = 0.5,
    max_seconds: float = 300.0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Stream a job's progress as Server-Sent Events until it completes."""
    _owned_job(job_id, db, user)  # authorize before streaming
    return StreamingResponse(
        _event_stream(job_id, poll_interval=poll_interval, max_seconds=max_seconds),
        media_type="text/event-stream",
    )
