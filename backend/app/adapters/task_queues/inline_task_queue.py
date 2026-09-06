"""Inline task queue -- runs the job in-process, immediately.

The dev/test adapter: no broker, no worker. ``enqueue`` awaits the runner so
that by the time it returns the job is already complete. Great for local runs
without Redis and for deterministic tests of the full ingestion pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.core.config import Settings


class InlineTaskQueue:
    """Executes ingestion jobs synchronously within the calling process."""

    name = "inline"

    def __init__(self) -> None:
        self._status: dict[str, str] = {}

    @classmethod
    def from_settings(cls, settings: Settings) -> InlineTaskQueue:
        return cls()

    async def enqueue(self, task_name: str, *args: Any, **kwargs: Any) -> str:
        from app.workers.ingest_runner import run_ingest_job

        document_id = kwargs["document_id"]
        job_id = kwargs["job_id"]
        status = await run_ingest_job(document_id, job_id)
        self._status[job_id] = status
        return job_id

    def get_status(self, job_id: str) -> str:
        return self._status.get(job_id, "unknown")
