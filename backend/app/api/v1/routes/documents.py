"""Document upload (async), bulk upload, and raw search routes."""

from __future__ import annotations

import io
import zipfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import embedder, storage, task_queue, vector_store
from app.api.v1.schemas import (
    BulkIngestResponse,
    BulkItem,
    DocumentOut,
    IngestAcceptedResponse,
    JobOut,
    SearchHit,
    SearchResponse,
)
from app.core.config import settings
from app.core.ratelimit import RateLimiter, get_rate_limiter
from app.db.base import get_db
from app.db.models import Document
from app.domain.interfaces import Embedder, ObjectStorage, TaskQueue, VectorStore
from app.services.document_service import DocumentService, UploadResult
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/documents", tags=["documents"])


def _doc_out(document: Document) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        org_id=document.org_id,
        owner_id=document.owner_id,
        filename=document.filename,
        mime_type=document.mime_type,
        checksum=document.checksum,
        storage_uri=document.storage_uri,
        status=document.status,
    )


def _job_out(result: UploadResult) -> JobOut | None:
    if result.job is None:
        return None
    job = result.job
    return JobOut(
        id=job.id,
        document_id=job.document_id,
        stage=job.stage,
        progress=job.progress,
        status=job.status,
        error=job.error,
        retries=job.retries,
    )


@router.post("", response_model=IngestAcceptedResponse, status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    object_storage: ObjectStorage = Depends(storage),
    queue: TaskQueue = Depends(task_queue),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> IngestAcceptedResponse:
    """Accept a file for ingestion: store it, dedup, and enqueue a job.

    Returns 202 with a ``job_id`` immediately; parsing/chunking/embedding/
    indexing run off the request thread. Poll ``GET /jobs/{id}`` for progress.
    """
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file upload")
    if not limiter.allow():
        raise HTTPException(status_code=429, detail="Ingestion rate limit exceeded")

    service = DocumentService(object_storage, queue, db)
    result = await service.upload(
        data=data,
        filename=file.filename or "upload.bin",
        content_type=file.content_type,
        org_id=settings.DEFAULT_ORG_ID,
        owner_id=settings.DEFAULT_ORG_ID,
    )
    return IngestAcceptedResponse(
        document=_doc_out(result.document),
        job=_job_out(result),
        deduped=result.deduped,
    )


@router.post("/bulk", response_model=BulkIngestResponse, status_code=202)
async def bulk_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    object_storage: ObjectStorage = Depends(storage),
    queue: TaskQueue = Depends(task_queue),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> BulkIngestResponse:
    """Accept a ZIP of documents and enqueue an ingestion job for each entry."""
    raw = await file.read()
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Not a valid ZIP file") from exc

    entries = [
        info
        for info in archive.infolist()
        if not info.is_dir() and not info.filename.startswith("__MACOSX/")
    ]
    if len(entries) > settings.MAX_BULK_DOCS:
        raise HTTPException(
            status_code=413,
            detail=f"Bulk upload exceeds MAX_BULK_DOCS ({settings.MAX_BULK_DOCS})",
        )
    if not limiter.allow(len(entries)):
        raise HTTPException(status_code=429, detail="Ingestion rate limit exceeded")

    service = DocumentService(object_storage, queue, db)
    items: list[BulkItem] = []
    accepted = 0
    for info in entries:
        payload = archive.read(info)
        if not payload:
            items.append(BulkItem(filename=info.filename, error="empty entry"))
            continue
        result = await service.upload(
            data=payload,
            filename=info.filename,
            content_type=None,
            org_id=settings.DEFAULT_ORG_ID,
            owner_id=settings.DEFAULT_ORG_ID,
        )
        accepted += 1
        items.append(
            BulkItem(
                filename=info.filename,
                document=_doc_out(result.document),
                job=_job_out(result),
                deduped=result.deduped,
            )
        )

    return BulkIngestResponse(accepted=accepted, items=items)


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    q: str,
    top_k: int = 5,
    document_embedder: Embedder = Depends(embedder),
    store: VectorStore = Depends(vector_store),
) -> SearchResponse:
    """Raw dense similarity search over indexed chunks (Phase 3)."""
    ingestion = IngestionService(embedder=document_embedder, vector_store=store)
    hits = await ingestion.search(q, namespace=settings.DEFAULT_ORG_ID, top_k=top_k)
    return SearchResponse(
        query=q,
        hits=[
            SearchHit(
                chunk_id=h.chunk.id,
                document_id=h.chunk.metadata.document_id,
                text=h.chunk.text,
                score=h.score,
                page=h.chunk.metadata.page,
                heading_path=h.chunk.metadata.heading_path,
            )
            for h in hits
        ],
    )


@router.get("", response_model=list[DocumentOut])
async def list_documents(db: Session = Depends(get_db)) -> list[DocumentOut]:
    stmt = select(Document).where(Document.org_id == settings.DEFAULT_ORG_ID)
    return [_doc_out(d) for d in db.execute(stmt).scalars().all()]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: str, db: Session = Depends(get_db)) -> DocumentOut:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_out(document)
