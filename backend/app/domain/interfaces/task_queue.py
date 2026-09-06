"""TaskQueue port -- enqueues durable background jobs.

Celery is the adapter today; Arq or RQ can replace it later without touching
the ingestion service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.core.config import Settings


@runtime_checkable
class TaskQueue(Protocol):
    """Any background task queue must satisfy this."""

    name: str  # "celery" | "arq" | "rq" | ...

    @classmethod
    def from_settings(cls, settings: Settings) -> TaskQueue:
        """Construct the adapter from application settings."""
        ...

    async def enqueue(self, task_name: str, *args: Any, **kwargs: Any) -> str:
        """Schedule a task and return its job id.

        Async so an in-process (inline) adapter can await the work while a real
        broker adapter (Celery) returns as soon as the job is queued.
        """
        ...

    def get_status(self, job_id: str) -> str:
        """Return the current status of a job."""
        ...
