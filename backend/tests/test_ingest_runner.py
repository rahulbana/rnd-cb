"""IngestionJobRunner: progress, retry/backoff, dead-letter, idempotency."""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.adapters.chunkers import StructureAwareChunker
from app.adapters.embedders import FakeEmbedder
from app.adapters.parsers import FakeParser
from app.adapters.storage import FakeObjectStorage
from app.adapters.vector_stores import FakeVectorStore
from app.db.base import Base
from app.db.models import ChunkMeta, Document, IngestionJob
from app.domain.models import EmbeddingVector
from app.services.ingestion_service import IngestionService
from app.services.storage_keys import object_key
from app.workers.ingest_runner import IngestionJobRunner


class _FlakyEmbedder(FakeEmbedder):
    """Fails ``fail_times`` document embeds, then behaves normally."""

    def __init__(self, fail_times: int) -> None:
        super().__init__()
        self._fail_times = fail_times

    async def embed_documents(self, texts: Sequence[str]) -> list[EmbeddingVector]:
        if self._fail_times > 0:
            self._fail_times -= 1
            raise RuntimeError("induced embedding failure")
        return await super().embed_documents(texts)


@pytest.fixture
def session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'runner.db'}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, future=True)
    db = maker()
    yield db
    db.close()
    engine.dispose()


async def _seed(session, storage, *, org="org-1", text=b"alpha beta\ngamma delta"):
    checksum = "sum123"
    filename = "doc.txt"
    document = Document(
        org_id=org,
        owner_id=org,
        filename=filename,
        mime_type="text/plain",
        checksum=checksum,
        storage_uri="fake://x",
        status="pending",
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    job = IngestionJob(document_id=document.id, stage="parsing", status="queued")
    session.add(job)
    session.commit()
    session.refresh(job)
    await storage.put(
        object_key(org, checksum, filename), text, content_type="text/plain"
    )
    return document, job


def _runner(session, storage, embedder, **kw):
    ingestion = IngestionService(
        embedder=embedder, vector_store=FakeVectorStore(), chunker=StructureAwareChunker()
    )
    return IngestionJobRunner(
        session, storage, FakeParser(), ingestion, backoff_base=0.0, **kw
    )


@pytest.mark.asyncio
async def test_success_updates_progress_and_status(session):
    storage = FakeObjectStorage()
    document, job = await _seed(session, storage)
    runner = _runner(session, storage, FakeEmbedder())

    status = await runner.run(document.id, job.id)
    assert status == "completed"

    session.refresh(job)
    session.refresh(document)
    assert job.status == "completed"
    assert job.progress == 100
    assert document.status == "indexed"
    metas = (
        session.execute(select(ChunkMeta).where(ChunkMeta.document_id == document.id))
        .scalars()
        .all()
    )
    assert len(metas) >= 1


@pytest.mark.asyncio
async def test_retry_then_recover(session):
    storage = FakeObjectStorage()
    document, job = await _seed(session, storage)
    # Fails once (attempt 1), succeeds on attempt 2.
    runner = _runner(session, storage, _FlakyEmbedder(fail_times=1), max_attempts=3)

    status = await runner.run(document.id, job.id)
    assert status == "completed"
    session.refresh(job)
    assert job.status == "completed"
    assert job.retries == 1  # recovered after one failed attempt


@pytest.mark.asyncio
async def test_dead_letter_after_max_attempts(session):
    storage = FakeObjectStorage()
    document, job = await _seed(session, storage)
    runner = _runner(session, storage, _FlakyEmbedder(fail_times=99), max_attempts=3)

    status = await runner.run(document.id, job.id)
    assert status == "failed"
    session.refresh(job)
    assert job.status == "failed"
    assert job.retries == 3
    assert "induced embedding failure" in (job.error or "")


@pytest.mark.asyncio
async def test_idempotent_rerun(session):
    storage = FakeObjectStorage()
    document, job = await _seed(session, storage)
    runner = _runner(session, storage, FakeEmbedder())

    await runner.run(document.id, job.id)
    first = (
        session.execute(select(ChunkMeta).where(ChunkMeta.document_id == document.id))
        .scalars()
        .all()
    )
    n = len(first)

    # Re-run the same job: chunk metadata must not accumulate.
    await runner.run(document.id, job.id)
    second = (
        session.execute(select(ChunkMeta).where(ChunkMeta.document_id == document.id))
        .scalars()
        .all()
    )
    assert len(second) == n
