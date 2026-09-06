"""In-memory fake task queue -- runs nothing, records enqueued jobs."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.core.config import Settings


class FakeTaskQueue:
    """Records enqueued jobs and reports them as immediately ``queued``."""

    name = "fake"

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}

    @classmethod
    def from_settings(cls, settings: Settings) -> FakeTaskQueue:
        return cls()

    async def enqueue(self, task_name: str, *args: Any, **kwargs: Any) -> str:
        job_id = kwargs.get("job_id") or str(uuid.uuid4())
        self._jobs[job_id] = {"task": task_name, "args": args, "kwargs": kwargs}
        return job_id

    @property
    def jobs(self) -> dict[str, dict[str, Any]]:
        """Recorded (but not executed) jobs -- inspected by tests."""
        return self._jobs

    def get_status(self, job_id: str) -> str:
        return "queued" if job_id in self._jobs else "unknown"
