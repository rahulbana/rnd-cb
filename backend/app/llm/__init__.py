"""LLM provider factory. Provider is switchable via config or per-request."""
from __future__ import annotations

from ..config import get_settings
from .base import BaseLLM


def get_llm(provider: str | None = None) -> BaseLLM:
    provider = provider or get_settings().llm_provider
    if provider == "openai":
        from .openai_provider import OpenAILLM
        return OpenAILLM()
    if provider == "ollama":
        from .ollama_provider import OllamaLLM
        return OllamaLLM()
    raise ValueError(f"Unknown LLM provider: {provider}")
