"""Build the right provider from config, keeping the CLI backend-agnostic."""

from __future__ import annotations

from .base import LLMError, LLMProvider

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "ollama": "llama3",
}


def build_provider(
    provider: str,
    *,
    model: str | None = None,
    temperature: float = 0.2,
    timeout: float = 120.0,
    api_key: str | None = None,
    base_url: str | None = None,
    host: str | None = None,
) -> LLMProvider:
    """Instantiate a provider by name (``openai`` or ``ollama``)."""
    provider = provider.lower()
    model = model or DEFAULT_MODELS.get(provider)
    if not model:
        raise LLMError(f"Unknown provider '{provider}'. Use 'openai' or 'ollama'.")

    if provider == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(
            model=model,
            temperature=temperature,
            timeout=timeout,
            api_key=api_key,
            base_url=base_url,
        )
    if provider == "ollama":
        from .ollama_provider import OllamaProvider

        return OllamaProvider(
            model=model,
            temperature=temperature,
            timeout=timeout,
            host=host,
        )

    raise LLMError(f"Unknown provider '{provider}'. Use 'openai' or 'ollama'.")
