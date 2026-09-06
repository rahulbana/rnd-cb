"""Celery ingestion task.

A thin wrapper: retry/backoff/idempotency live in ``IngestionJobRunner`` so the
semantics are identical to the inline queue. The task just runs the async
runner to completion on the worker.
"""

from __future__ import annotations

import asyncio

from app.core.logging import get_logger
from app.workers.celery_app import celery_app
from app.workers.ingest_runner import run_ingest_job

logger = get_logger("worker.ingest")


@celery_app.task(name="ingest_document", bind=True)
def ingest_document(self, document_id: str, job_id: str) -> dict[str, str]:
    """Run one ingestion job to completion."""
    logger.info("ingest_document.received", document_id=document_id, job_id=job_id)
    status = asyncio.run(run_ingest_job(document_id, job_id))
    return {"document_id": document_id, "job_id": job_id, "status": status}
