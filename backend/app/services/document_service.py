"""Document upload orchestration (Phase 4, async path).

Store the raw file, dedup by checksum, create the document + ingestion job, and
enqueue the job. Parsing/chunking/embedding/indexing run off the request thread
in the ingestion job runner (Celery worker, or inline for dev/tests).

Depends only on the ObjectStorage and TaskQueue ports plus a DB session.
"""

from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import Document, IngestionJob
from app.domain.interfaces import ObjectStorage, TaskQueue
from app.services.storage_keys import object_key

logger = get_logger("service.document")

# Extension -> MIME fallbacks for types Python's mimetypes misses or varies on.
_EXT_MIME = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".eml": "message/rfc822",
}


def compute_checksum(data: bytes) -> str:
    """SHA-256 hex digest used for content-addressed dedup."""
    return hashlib.sha256(data).hexdigest()


def guess_mime_type(filename: str, provided: str | None) -> str:
    """Resolve a usable MIME type from the client value or the filename."""
    if provided and provided not in {"application/octet-stream", ""}:
        return provided
    suffix = Path(filename).suffix.lower()
    if suffix in _EXT_MIME:
        return _EXT_MIME[suffix]
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or provided or "application/octet-stream"


@dataclass
class UploadResult:
    document: Document
    job: IngestionJob | None
    deduped: bool


class DocumentService:
    """Upload a document and enqueue its ingestion job."""

    def __init__(
        self, storage: ObjectStorage, task_queue: TaskQueue, db: Session
    ) -> None:
        self._storage = storage
        self._task_queue = task_queue
        self._db = db

    def _find_existing(self, org_id: str, checksum: str) -> Document | None:
        stmt = select(Document).where(
            Document.org_id == org_id, Document.checksum == checksum
        )
        return self._db.execute(stmt).scalar_one_or_none()

    async def upload(
        self,
        *,
        data: bytes,
        filename: str,
        content_type: str | None,
        org_id: str,
        owner_id: str,
    ) -> UploadResult:
        mime_type = guess_mime_type(filename, content_type)
        checksum = compute_checksum(data)

        existing = self._find_existing(org_id, checksum)
        if existing is not None:
            logger.info(
                "upload_deduped",
                document_id=existing.id,
                checksum=checksum,
                filename=filename,
            )
            return UploadResult(document=existing, job=None, deduped=True)

        key = object_key(org_id, checksum, filename)
        storage_uri = await self._storage.put(key, data, content_type=mime_type)

        document = Document(
            org_id=org_id,
            owner_id=owner_id,
            filename=filename,
            mime_type=mime_type,
            checksum=checksum,
            storage_uri=storage_uri,
            status="pending",
        )
        self._db.add(document)
        self._db.commit()
        self._db.refresh(document)

        job = IngestionJob(
            document_id=document.id,
            stage="parsing",
            status="queued",
            progress=0,
        )
        self._db.add(job)
        self._db.commit()
        self._db.refresh(job)

        # Enqueue off-thread ingestion. Inline queue completes it before this
        # returns; Celery returns immediately and the worker processes it.
        await self._task_queue.enqueue(
            "ingest_document", document_id=document.id, job_id=job.id
        )

        # Reflect any status the (inline) run already advanced.
        self._db.refresh(document)
        self._db.refresh(job)

        logger.info(
            "upload_enqueued",
            document_id=document.id,
            job_id=job.id,
            mime_type=mime_type,
        )
        return UploadResult(document=document, job=job, deduped=False)
