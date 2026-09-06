"""End-to-end ingestion + raw similarity retrieval over injectable ports."""

from __future__ import annotations

import pytest

from app.adapters.chunkers import StructureAwareChunker
from app.adapters.embedders import FakeEmbedder
from app.adapters.vector_stores import FakeVectorStore
from app.domain.models import ParsedDocument, TextBlock
from app.services.ingestion_service import IngestionService


def _service() -> IngestionService:
    return IngestionService(
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore(),
        chunker=StructureAwareChunker(size=200, overlap=20),
    )


@pytest.mark.asyncio
async def test_index_then_retrieve_by_similarity():
    parsed = ParsedDocument(
        source_filename="d.md",
        mime_type="text/markdown",
        text_blocks=[
            TextBlock(
                text="the mitochondria is the powerhouse of the cell",
                page=1,
                heading_path="Biology",
            ),
            TextBlock(
                text="quarterly revenue grew twenty percent",
                page=2,
                heading_path="Finance",
            ),
        ],
    )
    service = _service()
    chunks = await service.index(parsed, document_id="doc1", namespace="org-1")
    assert len(chunks) == 2

    # Raw similarity search: querying a chunk's exact text retrieves it top-1
    # (the fake embedder is deterministic: same text -> same vector).
    hits = await service.search(
        "quarterly revenue grew twenty percent", namespace="org-1", top_k=2
    )
    assert hits
    assert hits[0].chunk.metadata.document_id == "doc1"
    assert "revenue" in hits[0].chunk.text


@pytest.mark.asyncio
async def test_namespace_isolation():
    service = _service()
    parsed = ParsedDocument(
        source_filename="d.txt",
        mime_type="text/plain",
        text_blocks=[TextBlock(text="secret org one content", page=1)],
    )
    await service.index(parsed, document_id="doc1", namespace="org-1")
    hits = await service.search("secret org one content", namespace="org-2", top_k=5)
    assert hits == []


@pytest.mark.asyncio
async def test_index_without_chunker_raises():
    service = IngestionService(embedder=FakeEmbedder(), vector_store=FakeVectorStore())
    parsed = ParsedDocument(source_filename="d.txt", mime_type="text/plain")
    with pytest.raises(RuntimeError):
        await service.index(parsed, document_id="d", namespace="org-1")
