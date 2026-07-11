"""LLM factory — returns a LangChain chat model for the configured provider.

Adding a new provider means adding a single branch here; the rest of the
codebase only ever talks to the returned ``BaseChatModel`` interface, so
providers stay fully interchangeable.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from deep_agent.config import LLMProvider, Settings, get_settings
from deep_agent.utils.logging import get_logger

logger = get_logger("llm.factory")


def _build_openai(settings: Settings) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for the 'openai' provider.")
    return ChatOpenAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        api_key=settings.openai_api_key,
        timeout=60,
        max_retries=2,
    )


def _build_anthropic(settings: Settings) -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic

    if not settings.anthropic_api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is required for the 'anthropic' provider."
        )
    return ChatAnthropic(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        api_key=settings.anthropic_api_key,
        timeout=60,
        max_retries=2,
    )


_BUILDERS = {
    LLMProvider.OPENAI: _build_openai,
    LLMProvider.ANTHROPIC: _build_anthropic,
}


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    """Return a cached chat model instance for the configured provider."""

    settings = get_settings()
    builder = _BUILDERS.get(settings.llm_provider)
    if builder is None:  # pragma: no cover - guarded by enum
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")

    logger.info(
        "Initialising LLM provider=%s model=%s",
        settings.llm_provider.value,
        settings.llm_model,
    )
    return builder(settings)
