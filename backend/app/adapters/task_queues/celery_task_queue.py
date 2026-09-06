"""Celery task queue adapter (production).

Enqueues the ingestion task on the Celery broker (Redis) and returns
immediately -- ingestion runs off the request thread in a separate worker
container. Job progress is read from the ``ingestion_jobs`` table, so status
does not depend on Celery's own result backend.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.core.config import Settings


class CeleryTaskQueue:
    """Schedules ingestion jobs on Celery."""

    name = "celery"

    @classmethod
    def from_settings(cls, settings: Settings) -> CeleryTaskQueue:
        return cls()

    async def enqueue(self, task_name: str, *args: Any, **kwargs: Any) -> str:
        # Imported lazily so constructing the adapter never imports Celery.
        from app.workers.tasks.ingest_document import ingest_document

        document_id = kwargs["document_id"]
        job_id = kwargs["job_id"]
        ingest_document.apply_async(args=[document_id, job_id], task_id=job_id)
        return job_id

    def get_status(self, job_id: str) -> str:
        from app.workers.celery_app import celery_app

        return celery_app.AsyncResult(job_id).status
