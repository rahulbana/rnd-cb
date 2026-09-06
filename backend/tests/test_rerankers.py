"""Reranker adapters and registry swap."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from app.adapters.rerankers import (
    CohereReranker,
    CrossEncoderReranker,
    FakeReranker,
    LLMReranker,
)
from app.core.config import settings
from app.core.registry import clear_registry_caches, get_reranker
from app.domain.models import (
    ChatMessage,
    Chunk,
    ChunkMetadata,
    LLMResponse,
    RetrievedChunk,
)


def _cand(cid: str, text: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=Chunk(id=cid, text=text, metadata=ChunkMetadata(document_id=cid)),
        score=score,
        source="dense",
    )


_CANDIDATES = [
    _cand("a", "the weather is sunny today", 0.9),
    _cand("b", "quarterly revenue grew twenty percent", 0.8),
    _cand("c", "a recipe for chocolate cake", 0.7),
]


@pytest.mark.asyncio
async def test_fake_reranker_reorders_by_relevance():
    reranker = FakeReranker()
    out = await reranker.rerank("revenue growth", _CANDIDATES, top_k=2)
    assert out[0].chunk.id == "b"  # most query-term overlap
    assert out[0].source == "reranker"
    assert len(out) == 2


class _ScriptedLLM:
    """A fake LLM that rates relevance by query-term overlap count."""

    name = "scripted"

    def __init__(self) -> None:
        self.model = "scripted"

    async def generate(
        self, messages: Sequence[ChatMessage], *, temperature: float = 0.2
    ) -> LLMResponse:
        text = messages[-1].content.lower()
        # QUERY: ... PASSAGE: ...
        query_part, _, passage = text.partition("passage:")
        query = query_part.replace("query:", "")
        qtokens = set(query.split())
        score = sum(1 for t in passage.split() if t in qtokens)
        return LLMResponse(content=str(score), provider="scripted", model="scripted")


@pytest.mark.asyncio
async def test_llm_reranker_uses_llm_scores():
    reranker = LLMReranker(_ScriptedLLM())
    out = await reranker.rerank("revenue percent", _CANDIDATES, top_k=1)
    assert out[0].chunk.id == "b"
    assert out[0].source == "reranker"


@pytest.mark.asyncio
async def test_empty_candidates():
    assert await FakeReranker().rerank("q", [], top_k=5) == []


def test_registry_swaps_reranker(monkeypatch):
    for provider, cls in [
        ("fake", FakeReranker),
        ("cross_encoder", CrossEncoderReranker),
        ("cohere", CohereReranker),
        ("llm", LLMReranker),
    ]:
        monkeypatch.setattr(settings, "RERANKER_PROVIDER", provider)
        clear_registry_caches()
        assert isinstance(get_reranker(), cls)


@pytest.mark.asyncio
async def test_cross_encoder_real_rerank():
    pytest.importorskip("sentence_transformers")
    reranker = CrossEncoderReranker(model=settings.RERANK_MODEL)
    out = await reranker.rerank("company revenue", _CANDIDATES, top_k=3)
    assert len(out) == 3
    assert out[0].source == "reranker"
