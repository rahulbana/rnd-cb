"""Real Chroma adapter test using an embedded ephemeral client.

Skips cleanly where chromadb is not installed (it is an optional extra).
"""

from __future__ import annotations

import pytest

pytest.importorskip("chromadb")

from app.adapters.vector_stores import ChromaVectorStore  # noqa: E402
from app.domain.models import (  # noqa: E402
    Chunk,
    ChunkMetadata,
    EmbeddingVector,
)


def _chunk(cid: str, text: str, page: int) -> Chunk:
    return Chunk(
        id=cid,
        text=text,
        metadata=ChunkMetadata(document_id="doc1", page=page, ordinal=int(cid[-1])),
    )


@pytest.fixture
def store():
    import chromadb

    return ChromaVectorStore(client=chromadb.EphemeralClient())


@pytest.mark.asyncio
async def test_upsert_search_delete_roundtrip(store):
    chunks = [
        _chunk("c0", "the cat sat on the mat", 1),
        _chunk("c1", "quarterly revenue grew by twenty percent", 2),
    ]
    vectors = [
        EmbeddingVector.of([1.0, 0.0, 0.0], model="t"),
        EmbeddingVector.of([0.0, 1.0, 0.0], model="t"),
    ]
    await store.upsert(chunks, vectors, namespace="org-1")

    # Query near the first vector -> first chunk ranks top.
    results = await store.search(
        EmbeddingVector.of([0.95, 0.05, 0.0], model="t"),
        namespace="org-1",
        top_k=2,
    )
    assert results
    assert results[0].chunk.id == "c0"
    assert results[0].chunk.metadata.document_id == "doc1"
    assert results[0].chunk.metadata.page == 1
    assert results[0].score > results[1].score

    await store.delete(["c0"], namespace="org-1")
    after = await store.search(
        EmbeddingVector.of([0.95, 0.05, 0.0], model="t"),
        namespace="org-1",
        top_k=2,
    )
    assert all(r.chunk.id != "c0" for r in after)


@pytest.mark.asyncio
async def test_namespaces_are_isolated(store):
    await store.upsert(
        [_chunk("c0", "org one doc", 1)],
        [EmbeddingVector.of([1.0, 0.0, 0.0], model="t")],
        namespace="org-1",
    )
    results = await store.search(
        EmbeddingVector.of([1.0, 0.0, 0.0], model="t"),
        namespace="org-2",
        top_k=5,
    )
    assert results == []
