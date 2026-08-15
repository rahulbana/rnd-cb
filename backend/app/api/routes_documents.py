"""Document upload and management endpoints.

Upload flow (two-step so no progress events are lost to a subscription race):
  1. POST /api/upload (or /api/text) persists the input and returns a job_id.
  2. The client opens WS /ws/ingest/{job_id}; the ingestion task starts only
     once that socket is connected, then streams parse->chunk->embed->index
     events.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..config import get_settings
from ..ingestion.router import SUPPORTED_EXTENSIONS
from ..vectorstore import get_vectorstore

router = APIRouter(prefix="/api", tags=["documents"])


@dataclass
class PendingJob:
    source_name: str
    path: str | None = None
    raw_text: str | None = None


# job_id -> PendingJob. Consumed (popped) when its ingest WS connects.
PENDING_JOBS: dict[str, PendingJob] = {}


@router.post("/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported type '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
        )
    settings = get_settings()
    os.makedirs(settings.upload_dir, exist_ok=True)
    job_id = uuid.uuid4().hex
    dest = os.path.join(settings.upload_dir, f"{job_id}{ext}")
    with open(dest, "wb") as out:
        while chunk := await file.read(1 << 20):  # 1 MiB
            out.write(chunk)
    PENDING_JOBS[job_id] = PendingJob(source_name=file.filename or dest, path=dest)
    return {"job_id": job_id, "source_name": file.filename}


class TextIn(BaseModel):
    text: str
    name: str | None = None


@router.post("/text")
async def upload_text(body: TextIn) -> dict:
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Empty text.")
    job_id = uuid.uuid4().hex
    name = body.name or f"text-{job_id[:8]}.txt"
    PENDING_JOBS[job_id] = PendingJob(source_name=name, raw_text=body.text)
    return {"job_id": job_id, "source_name": name}


@router.get("/sources")
async def list_sources() -> dict:
    store = get_vectorstore()
    return {"sources": store.list_sources(), "total_chunks": store.count()}


@router.delete("/sources/{source}")
async def delete_source(source: str) -> dict:
    store = get_vectorstore()
    store.delete_source(source)
    return {"deleted": source, "total_chunks": store.count()}
