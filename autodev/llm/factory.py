"""Build the configured LLM provider."""
from __future__ import annotations

from ..config import Settings, get_settings
from .base import LLMProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider


def build_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    provider = (settings.llm_provider or "openai").lower()

    if provider == "openai":
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            timeout=settings.request_timeout,
        )
    if provider == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.request_timeout,
        )
    raise ValueError(f"Unknown AUTODEV_LLM_PROVIDER: {settings.llm_provider!r}")
