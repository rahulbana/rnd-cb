"""Every fake adapter must structurally satisfy its port Protocol."""

from __future__ import annotations

import pytest

from app.adapters.chunkers import FakeChunker
from app.adapters.embedders import FakeEmbedder, FakeHashEmbedder
from app.adapters.llm_providers import FakeLLMProvider
from app.adapters.parsers import FakeParser
from app.adapters.rerankers import FakeReranker
from app.adapters.storage import FakeObjectStorage
from app.adapters.task_queues import FakeTaskQueue
from app.adapters.vector_stores import FakeVectorStore
from app.domain.interfaces import (
    Chunker,
    Embedder,
    LLMProvider,
    ObjectStorage,
    Parser,
    Reranker,
    TaskQueue,
    VectorStore,
)
from app.domain.models import ChatMessage, Role


@pytest.mark.parametrize(
    "adapter, port",
    [
        (FakeLLMProvider(), LLMProvider),
        (FakeEmbedder(), Embedder),
        (FakeHashEmbedder(), Embedder),
        (FakeVectorStore(), VectorStore),
        (FakeReranker(), Reranker),
        (FakeParser(), Parser),
        (FakeChunker(), Chunker),
        (FakeObjectStorage(), ObjectStorage),
        (FakeTaskQueue(), TaskQueue),
    ],
)
def test_adapter_satisfies_port(adapter, port):
    assert isinstance(adapter, port)


@pytest.mark.asyncio
async def test_end_to_end_wiring_with_fakes():
    """Parse -> chunk -> embed -> store -> retrieve, all fakes, no network."""
    parser = FakeParser()
    chunker = FakeChunker()
    embedder = FakeEmbedder()
    store = FakeVectorStore()

    parsed = await parser.parse(
        b"alpha beta\ngamma delta", filename="a.txt", mime_type="text/plain"
    )
    chunks = chunker.chunk(parsed, document_id="doc1")
    assert len(chunks) == 2

    vectors = await embedder.embed_documents([c.text for c in chunks])
    await store.upsert(chunks, vectors, namespace="org1")

    query_vec = await embedder.embed_query("alpha beta")
    results = await store.search(query_vec, namespace="org1", top_k=2)
    assert results
    assert results[0].chunk.text == "alpha beta"


@pytest.mark.asyncio
async def test_fake_llm_generates():
    llm = FakeLLMProvider()
    resp = await llm.generate([ChatMessage(role=Role.USER, content="hi there")])
    assert "hi there" in resp.content
    assert resp.provider == "fake"
