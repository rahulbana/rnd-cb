"""LLM client wrapper supporting OpenAI and Ollama (OpenAI-compatible API).

Both providers use the `openai` SDK; Ollama is reached by pointing `base_url`
at its local OpenAI-compatible endpoint. The provider can be switched at
runtime (see config.set_llm), so the client is cached per provider signature
and invalidated via reset_client_cache().
"""
from __future__ import annotations

from ..config import config


class LLMUnavailable(RuntimeError):
    """Raised when the active LLM provider is not usable."""


_client_cache: dict = {}


def get_client():
    """Return a client for the active provider, or raise LLMUnavailable."""
    provider = config.active_provider()
    if provider == "openai" and not config.OPENAI_API_KEY:
        raise LLMUnavailable(
            "OPENAI_API_KEY is not configured. Add it to your .env file, or switch "
            "the provider to Ollama to run a local model."
        )

    # Cache key captures everything that affects which server we talk to.
    key = (provider, config.llm_base_url(), config.llm_api_key())
    client = _client_cache.get(key)
    if client is None:
        from openai import OpenAI

        client = OpenAI(api_key=config.llm_api_key(), base_url=config.llm_base_url())
        _client_cache[key] = client
    return client


def reset_client_cache() -> None:
    """Drop cached clients (call after switching provider/model)."""
    _client_cache.clear()


def complete(system: str, user: str, *, temperature: float = 0.2,
             max_tokens: int = 1200, model: str | None = None) -> str:
    """Single-shot chat completion returning the assistant's text."""
    client = get_client()
    resp = client.chat.completions.create(
        model=model or config.active_model(),
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (resp.choices[0].message.content or "").strip()
