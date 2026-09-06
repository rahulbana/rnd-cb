"""Embedder adapter tests (fakes run always; real ones are gated)."""

from __future__ import annotations

import pytest

from app.adapters.embedders import (
    FakeEmbedder,
    OpenAIEmbedder,
    SentenceTransformersEmbedder,
)


@pytest.mark.asyncio
async def test_fake_embedder_dim_and_determinism():
    emb = FakeEmbedder()
    a = await emb.embed_query("hello")
    b = await emb.embed_query("hello")
    assert a.dim == emb.dim
    assert a.values == b.values  # deterministic
    docs = await emb.embed_documents(["one", "two"])
    assert len(docs) == 2
    assert all(v.dim == emb.dim for v in docs)


def test_real_embedders_construct_without_loading():
    """Constructing real embedders must not import heavy libs or hit network."""
    from app.core.config import settings

    st = SentenceTransformersEmbedder.from_settings(settings)
    assert st.name == "sentence_transformers"
    assert st.dim == settings.EMBED_DIM

    oa = OpenAIEmbedder.from_settings(settings)
    assert oa.name == "openai"
    assert oa.dim == settings.OPENAI_EMBED_DIM


@pytest.mark.asyncio
async def test_sentence_transformers_real_embed():
    st_module = pytest.importorskip("sentence_transformers")  # noqa: F841
    from app.core.config import settings

    emb = SentenceTransformersEmbedder(model=settings.EMBED_MODEL, dim=settings.EMBED_DIM)
    vec = await emb.embed_query("hello world")
    assert vec.dim == settings.EMBED_DIM
    assert len(vec.values) == settings.EMBED_DIM
