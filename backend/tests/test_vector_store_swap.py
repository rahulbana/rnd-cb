"""Phase 3 EXIT TEST (vector-store half).

Switching ``VECTOR_STORE_PROVIDER`` from chroma to pgvector (or fake) requires
zero code changes: the call site ``get_vector_store()`` is identical; only the
env value changes. Construction is lazy, so this proves the swap without any
vector DB running.
"""

from __future__ import annotations

from app.adapters.vector_stores import (
    ChromaVectorStore,
    FakeVectorStore,
    PgVectorStore,
)
from app.core.config import settings
from app.core.registry import clear_registry_caches, get_vector_store


def _resolve_with(monkeypatch, provider: str):
    monkeypatch.setattr(settings, "VECTOR_STORE_PROVIDER", provider)
    clear_registry_caches()
    return get_vector_store()


def test_swap_chroma_to_pgvector_zero_code_change(monkeypatch):
    chroma = _resolve_with(monkeypatch, "chroma")
    assert isinstance(chroma, ChromaVectorStore)
    assert chroma.name == "chroma"

    pg = _resolve_with(monkeypatch, "pgvector")
    assert isinstance(pg, PgVectorStore)
    assert pg.name == "pgvector"

    fake = _resolve_with(monkeypatch, "fake")
    assert isinstance(fake, FakeVectorStore)

    # Same call site, three different implementations.
    assert type(chroma) is not type(pg) is not type(fake)
