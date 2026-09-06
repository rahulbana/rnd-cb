"""Phase 1 EXIT TEST.

Flipping one env var swaps the fake embedder for a *second* fake
implementation with no code change. Proven here: the call site
(``get_embedder``) is identical; only ``settings.EMBEDDER_PROVIDER`` changes.
"""

from __future__ import annotations

import pytest

from app.adapters.embedders import FakeEmbedder, FakeHashEmbedder
from app.core import registry
from app.core.config import settings
from app.core.registry import clear_registry_caches, get_embedder


@pytest.mark.asyncio
async def test_env_var_swaps_embedder_implementation(monkeypatch):
    # Default wiring -> first fake.
    monkeypatch.setattr(settings, "EMBEDDER_PROVIDER", "fake")
    clear_registry_caches()
    first = get_embedder()
    assert isinstance(first, FakeEmbedder)
    assert first.name == "fake"
    vec_a = await first.embed_query("hello world")

    # Flip ONE env value -> second fake. No consumer code changed.
    monkeypatch.setattr(settings, "EMBEDDER_PROVIDER", "fake_hash")
    clear_registry_caches()
    second = get_embedder()
    assert isinstance(second, FakeHashEmbedder)
    assert second.name == "fake_hash"
    vec_b = await second.embed_query("hello world")

    # Same interface, genuinely different implementation.
    assert type(first) is not type(second)
    assert vec_a.model != vec_b.model
    assert vec_a.values != vec_b.values


def test_unknown_provider_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDER_PROVIDER", "does_not_exist")
    clear_registry_caches()
    with pytest.raises(ValueError) as exc:
        get_embedder()
    assert "Unknown embedder provider" in str(exc.value)


def test_every_port_resolves_to_an_adapter():
    """The whole system is wired: every factory returns an instance."""
    factories = [
        registry.get_llm_provider,
        registry.get_embedder,
        registry.get_vector_store,
        registry.get_reranker,
        registry.get_retriever,
        registry.get_parser,
        registry.get_chunker,
        registry.get_storage,
        registry.get_task_queue,
    ]
    for factory in factories:
        instance = factory()
        assert instance is not None
        assert hasattr(instance, "name")
