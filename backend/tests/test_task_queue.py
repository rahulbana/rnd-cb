"""TaskQueue adapters and registry swap."""

from __future__ import annotations

import pytest

from app.adapters.task_queues import CeleryTaskQueue, FakeTaskQueue, InlineTaskQueue
from app.core.config import settings
from app.core.registry import clear_registry_caches, get_task_queue


@pytest.mark.asyncio
async def test_fake_records_without_running():
    queue = FakeTaskQueue()
    job_id = await queue.enqueue("ingest_document", document_id="d1", job_id="j1")
    assert job_id == "j1"
    assert "j1" in queue.jobs
    assert queue.get_status("j1") == "queued"
    assert queue.get_status("nope") == "unknown"


def test_registry_swaps_task_queue(monkeypatch):
    for provider, cls in [
        ("fake", FakeTaskQueue),
        ("inline", InlineTaskQueue),
        ("celery", CeleryTaskQueue),
    ]:
        monkeypatch.setattr(settings, "TASK_QUEUE_PROVIDER", provider)
        clear_registry_caches()
        assert isinstance(get_task_queue(), cls)


def test_celery_adapter_constructs_without_broker():
    # Construction must not connect to Redis.
    queue = CeleryTaskQueue.from_settings(settings)
    assert queue.name == "celery"
