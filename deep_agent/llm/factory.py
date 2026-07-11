"""LLM factory — provider-agnostic, per-agent-configurable chat models.

A single ``get_chat_model`` builds (and caches) a LangChain chat model for
the configured provider, resolving the model name from:

1. an explicit per-agent override (``LLM_AGENT_MODELS``),
2. the FAST-tier model (``LLM_FAST_MODEL``) when the caller asks for it,
3. the default ``LLM_MODEL``.

Fine-grained params (``max_tokens``, ``timeout``, ``max_retries``, ``seed``)
are applied uniformly, and an optional response cache dedupes identical
calls (across runs with the SQLite backend).
"""
from __future__ import annotations

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from deep_agent.config import (
    CacheBackend,
    LLMProvider,
    LLMTier,
    Settings,
    get_settings,
)
from deep_agent.utils.logging import get_logger

logger = get_logger("llm.factory")

_CACHE_CONFIGURED = False


def _init_llm_cache(settings: Settings) -> None:
    """Configure a global LangChain LLM cache once per process."""

    global _CACHE_CONFIGURED
    if _CACHE_CONFIGURED:
        return

    from langchain_core.globals import set_llm_cache

    backend = settings.llm_cache_backend
    if backend is CacheBackend.NONE:
        set_llm_cache(None)
    elif backend is CacheBackend.SQLITE:
        try:
            from langchain_community.cache import SQLiteCache

            set_llm_cache(SQLiteCache(database_path=settings.llm_cache_path))
            logger.info("LLM cache: sqlite → %s", settings.llm_cache_path)
        except Exception as exc:  # noqa: BLE001 - fall back to memory
            from langchain_core.caches import InMemoryCache

            logger.warning(
                "SQLite LLM cache unavailable (%s); using in-memory cache.", exc
            )
            set_llm_cache(InMemoryCache())
    else:  # MEMORY
        from langchain_core.caches import InMemoryCache

        set_llm_cache(InMemoryCache())
        logger.info("LLM cache: in-memory")

    _CACHE_CONFIGURED = True


def _resolve_model(settings: Settings, role: str | None, tier: LLMTier) -> str:
    """Resolve the model name for a given agent role and tier."""

    if role and role in settings.llm_agent_models:
        return settings.llm_agent_models[role]
    if tier is LLMTier.FAST and settings.llm_fast_model:
        return settings.llm_fast_model
    return settings.llm_model


def _build_openai(settings: Settings, model: str) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for the 'openai' provider.")
    kwargs: dict = dict(
        model=model,
        temperature=settings.llm_temperature,
        api_key=settings.openai_api_key,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
    )
    if settings.llm_max_tokens is not None:
        kwargs["max_tokens"] = settings.llm_max_tokens
    if settings.llm_seed is not None:
        kwargs["seed"] = settings.llm_seed
    return ChatOpenAI(**kwargs)


def _build_anthropic(settings: Settings, model: str) -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic

    if not settings.anthropic_api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is required for the 'anthropic' provider."
        )
    kwargs: dict = dict(
        model=model,
        temperature=settings.llm_temperature,
        api_key=settings.anthropic_api_key,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
        # Anthropic requires an explicit max_tokens; default when unset.
        max_tokens=settings.llm_max_tokens or 4096,
    )
    return ChatAnthropic(**kwargs)


_BUILDERS = {
    LLMProvider.OPENAI: _build_openai,
    LLMProvider.ANTHROPIC: _build_anthropic,
}


@lru_cache(maxsize=16)
def _cached_model(provider: LLMProvider, model: str) -> BaseChatModel:
    """Build (once) and cache a model per (provider, model) pair."""

    settings = get_settings()
    _init_llm_cache(settings)
    builder = _BUILDERS.get(provider)
    if builder is None:  # pragma: no cover - guarded by enum
        raise ValueError(f"Unsupported LLM provider: {provider}")
    logger.info("Initialising LLM provider=%s model=%s", provider.value, model)
    return builder(settings, model)


def get_chat_model(
    role: str | None = None, tier: LLMTier = LLMTier.SMART
) -> BaseChatModel:
    """Return a chat model for an agent ``role`` at the requested ``tier``."""

    settings = get_settings()
    model = _resolve_model(settings, role, tier)
    return _cached_model(settings.llm_provider, model)
