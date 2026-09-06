"""ContextAssembler: dedup, MMR, token budget, citations, compression."""

from __future__ import annotations

from app.domain.models import Chunk, ChunkMetadata, RetrievedChunk
from app.services.context_assembly import ContextAssembler


def _c(cid: str, text: str, score: float, *, page: int = 1) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=Chunk(
            id=cid,
            text=text,
            metadata=ChunkMetadata(document_id=f"doc-{cid}", page=page),
        ),
        score=score,
        source="reranker",
    )


def test_dedup_removes_near_identical():
    chunks = [
        _c("a", "the quick brown fox jumps over the lazy dog", 0.9),
        _c("b", "the quick brown fox jumps over the lazy dog", 0.8),  # dup
        _c("c", "completely different content about finance", 0.7),
    ]
    ctx = ContextAssembler().assemble("fox", chunks)
    ids = {c.chunk.id for c in ctx.chunks}
    assert "a" in ids and "c" in ids
    assert "b" not in ids  # near-identical dropped


def test_token_budget_limits_packing():
    big = " ".join(["word"] * 100)
    chunks = [_c("a", big, 0.9), _c("b", big, 0.8), _c("c", big, 0.7)]
    ctx = ContextAssembler(token_budget=150).assemble("word", chunks)
    # 150 tokens fits only the first ~100-word chunk plus its marker.
    assert len(ctx.chunks) == 1


def test_citations_tagged_with_source():
    chunks = [_c("a", "alpha content", 0.9, page=3)]
    ctx = ContextAssembler().assemble("alpha", chunks)
    assert ctx.citations[0].document_id == "doc-a"
    assert ctx.citations[0].page == 3
    assert ctx.citations[0].chunk_id == "a"
    assert "[1]" in ctx.text


def test_mmr_diversifies():
    # Two near-duplicates (high score) + one diverse; MMR should surface the
    # diverse chunk rather than stacking both similar ones.
    chunks = [
        _c("a", "machine learning training data models", 1.0),
        _c("b", "machine learning training data models pipeline", 0.95),
        _c("c", "olive oil mediterranean vegetables recipe", 0.5),
    ]
    # Diversity-weighted MMR (low lambda) surfaces the diverse chunk 'c' ahead
    # of the second near-duplicate 'b'.
    ctx = ContextAssembler(mmr_lambda=0.3, dedup_threshold=0.99).assemble("ml", chunks)
    order = [c.chunk.id for c in ctx.chunks]
    assert order.index("c") < order.index("b")


def test_contextual_compression_drops_irrelevant_sentences():
    text = "Revenue grew this year. The cafeteria menu changed. Revenue was strong."
    chunks = [_c("a", text, 0.9)]
    ctx = ContextAssembler(compress=True).assemble("revenue", chunks)
    assert "cafeteria" not in ctx.chunks[0].chunk.text
    assert "Revenue" in ctx.chunks[0].chunk.text
