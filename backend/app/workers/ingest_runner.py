"""Durable ingestion job runner.

Owns the resumable, observable, idempotent ingestion pipeline. Celery and the
inline task queue both call this; retry/backoff/dead-letter live here (not in
Celery) so the semantics are identical regardless of the queue adapter.

Stages: parsing -> chunking -> embedding -> indexing -> completed, with the
job row updated after each so progress is visible mid-flight. Re-runs are
idempotent: prior chunks (and their vectors) are cleared before re-indexing.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import ChunkMeta, Document, IngestionJob
from app.domain.interfaces import ObjectStorage, Parser
from app.services.ingestion_service import IngestionService
from app.services.storage_keys import object_key

logger = get_logger("worker.ingest_runner")

# Terminal statuses.
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"  # dead-letter


class IngestionJobRunner:
    """Runs one ingestion job to completion, with retries and progress."""

    def __init__(
        self,
        db: Session,
        storage: ObjectStorage,
        parser: Parser,
        ingestion: IngestionService,
        *,
        max_attempts: int = 3,
        backoff_base: float = 0.5,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._db = db
        self._storage = storage
        self._parser = parser
        self._ingestion = ingestion
        self._max_attempts = max_attempts
        self._backoff_base = backoff_base
        self._sleep = sleep

    async def run(self, document_id: str, job_id: str) -> str:
        """Run the job, retrying with backoff. Returns the terminal status.

        On exhausting retries the job is dead-lettered (status=failed) and the
        exception is swallowed so the worker process stays healthy.
        """
        for attempt in range(1, self._max_attempts + 1):
            try:
                await self._run_once(document_id, job_id)
                return STATUS_COMPLETED
            except Exception as exc:  # noqa: BLE001 - durability boundary
                job = self._db.get(IngestionJob, job_id)
                if job is not None:
                    job.retries = attempt
                    job.error = str(exc)
                    job.status = "retrying"
                    self._db.commit()
                logger.warning(
                    "ingest_attempt_failed",
                    job_id=job_id,
                    document_id=document_id,
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt >= self._max_attempts:
                    if job is not None:
                        job.status = STATUS_FAILED
                        self._db.commit()
                    logger.error(
                        "ingest_dead_letter", job_id=job_id, document_id=document_id
                    )
                    return STATUS_FAILED
                await self._sleep(self._backoff_base * (2 ** (attempt - 1)))
        return STATUS_FAILED

    async def _run_once(self, document_id: str, job_id: str) -> None:
        job = self._db.get(IngestionJob, job_id)
        document = self._db.get(Document, document_id)
        if job is None or document is None:
            raise RuntimeError(f"job {job_id} or document {document_id} not found")

        def progress(stage: str, percent: int) -> None:
            job.stage = stage
            job.progress = percent
            job.status = "running"
            self._db.commit()

        # Idempotency: clear any prior chunks + their vectors first.
        await self._clear_previous(document)

        progress("parsing", 10)
        key = object_key(document.org_id, document.checksum, document.filename)
        data = await self._storage.get(key)
        parsed = await self._parser.parse(
            data, filename=document.filename, mime_type=document.mime_type
        )

        chunks = await self._ingestion.index(
            parsed,
            document_id=document.id,
            namespace=document.org_id,
            on_stage=progress,
        )

        for chunk in chunks:
            self._db.add(
                ChunkMeta(
                    document_id=document.id,
                    page=chunk.metadata.page,
                    heading_path=chunk.metadata.heading_path,
                    vector_id=chunk.id,
                    text=chunk.text,
                )
            )

        job.stage = "indexing"
        job.progress = 100
        job.status = STATUS_COMPLETED
        job.error = None
        document.status = "indexed"
        self._db.commit()

        logger.info(
            "ingest_completed",
            job_id=job_id,
            document_id=document_id,
            chunks=len(chunks),
        )

    async def _clear_previous(self, document: Document) -> None:
        """Delete prior chunk metadata and vectors for a clean, idempotent re-run."""
        stmt = select(ChunkMeta).where(ChunkMeta.document_id == document.id)
        existing = self._db.execute(stmt).scalars().all()
        if not existing:
            return
        vector_ids = [c.vector_id for c in existing]
        await self._ingestion.remove(vector_ids, namespace=document.org_id)
        for meta in existing:
            self._db.delete(meta)
        self._db.commit()


async def run_ingest_job(document_id: str, job_id: str) -> str:
    """Build a runner from the registry and run one job to completion.

    The single entry point both the Celery task and the inline task queue use,
    so the async worker resolves its ports from the registry (not request-
    injected dependencies).
    """
    from app.core.config import settings
    from app.core.registry import (
        get_chunker,
        get_embedder,
        get_parser,
        get_storage,
        get_vector_store,
    )
    from app.db.base import SessionLocal

    db = SessionLocal()
    try:
        ingestion = IngestionService(
            embedder=get_embedder(),
            vector_store=get_vector_store(),
            chunker=get_chunker(),
        )
        runner = IngestionJobRunner(
            db,
            get_storage(),
            get_parser(),
            ingestion,
            max_attempts=settings.INGEST_MAX_ATTEMPTS,
            backoff_base=settings.INGEST_BACKOFF_BASE,
        )
        return await runner.run(document_id, job_id)
    finally:
        db.close()
