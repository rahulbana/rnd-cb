"""Celery application factory.

The scraper agent offloads page fetching to Celery so that scraping can be
parallelised across workers.  For local / CI use, ``CELERY_TASK_ALWAYS_EAGER``
makes tasks run inline (no broker or worker required).

Run a worker with::

    celery -A deep_agent.tasks.celery_app:celery_app worker --loglevel=info
"""
from __future__ import annotations

from celery import Celery

from deep_agent.config import get_settings

settings = get_settings()

celery_app = Celery(
    "deep_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["deep_agent.tasks.scraping", "deep_agent.tasks.search"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=120,
    task_soft_time_limit=90,
    worker_max_tasks_per_child=200,
    # When true, tasks execute synchronously in-process (no broker needed).
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
)
