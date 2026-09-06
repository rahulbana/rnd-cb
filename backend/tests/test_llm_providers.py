"""LLM provider adapters and registry swap (Phase 7 exit, provider half)."""

from __future__ import annotations

import pytest

from app.adapters.llm_providers import (
    AnthropicProvider,
    FakeLLMProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAIProvider,
)
from app.core.config import settings
from app.core.registry import clear_registry_caches, get_llm_provider
from app.domain.models import ChatMessage, Role


def test_registry_swaps_llm_provider(monkeypatch):
    """Flipping LLM_PROVIDER swaps the implementation -- zero code change."""
    for provider, cls in [
        ("fake", FakeLLMProvider),
        ("openai", OpenAIProvider),
        ("anthropic", AnthropicProvider),
        ("gemini", GeminiProvider),
        ("ollama", OllamaProvider),
    ]:
        monkeypatch.setattr(settings, "LLM_PROVIDER", provider)
        clear_registry_caches()
        got = get_llm_provider()
        assert isinstance(got, cls)
        assert got.name == provider


def test_real_providers_construct_without_network():
    """Construction must not import SDKs or open connections."""
    assert OpenAIProvider.from_settings(settings).name == "openai"
    assert AnthropicProvider.from_settings(settings).name == "anthropic"
    assert GeminiProvider.from_settings(settings).name == "gemini"
    assert OllamaProvider.from_settings(settings).name == "ollama"


@pytest.mark.asyncio
async def test_fake_provider_generate_and_stream():
    llm = FakeLLMProvider()
    messages = [ChatMessage(role=Role.USER, content="hello there")]
    resp = await llm.generate(messages)
    assert "hello there" in resp.content
    assert resp.provider == "fake"

    streamed = "".join([tok async for tok in llm.stream(messages)])
    assert "hello there" in streamed
    assert llm.count_tokens("a b c") == 3
