"""Ingestion task skeleton.

Phase 1 registers the task so the worker boots and health-checks. The real
parse -> chunk -> embed -> index pipeline is filled in across Phases 2-4;
the task signature and registration do not change.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger("worker.ingest")


@celery_app.task(name="ingest_document", bind=True, max_retries=3)
def ingest_document(self, document_id: str) -> dict[str, str]:
    """Placeholder ingestion task -- wired, not yet doing work."""
    logger.info("ingest_document.received", document_id=document_id)
    return {"document_id": document_id, "status": "accepted"}
