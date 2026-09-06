"""Celery application.

Phase 1 stands up the worker container and broker wiring so Phase 4 can move
ingestion off the request thread by adding a task, not new infrastructure.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "rag-platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Import task modules explicitly so they register with the app.
from app.workers.tasks import ingest_document  # noqa: E402,F401
