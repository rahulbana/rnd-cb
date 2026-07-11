"""LLM factory — registry-driven, per-agent-configurable chat models.

``get_chat_model`` resolves the model name for an agent role/tier, looks up
the configured provider in the registry, validates its credential, applies
fine-grained params and returns a cached chat model.  Adding a provider
never touches this file — only ``providers.py`` / ``register_provider``.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from deep_agent.config import CacheBackend, LLMTier, Settings, get_settings
from deep_agent.llm.base import LLMParams

# Importing providers registers the built-ins (openai/anthropic/google).
from deep_agent.llm import providers as _providers  # noqa: F401
from deep_agent.llm.registry import get_provider
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


@lru_cache(maxsize=32)
def _cached_model(provider_name: str, model: str) -> BaseChatModel:
    """Build (once) and cache a model per (provider, model) pair."""

    settings = get_settings()
    spec = get_provider(provider_name)

    if not spec.get_api_key(settings):
        raise ValueError(
            f"{spec.env_key} is required for the '{spec.name}' LLM provider. "
            "Set it in your environment or .env."
        )

    _init_llm_cache(settings)
    params = LLMParams(
        model=model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
        seed=settings.llm_seed,
    )
    logger.info("Initialising LLM provider=%s model=%s", spec.name, model)
    try:
        return spec.build(settings, params)
    except ImportError as exc:  # pragma: no cover - depends on env
        raise ImportError(
            f"The '{spec.name}' provider requires '{spec.package}'. "
            f"Install it with: pip install {spec.package}  ({exc})"
        ) from exc


def get_chat_model(
    role: str | None = None, tier: LLMTier = LLMTier.SMART
) -> BaseChatModel:
    """Return a chat model for an agent ``role`` at the requested ``tier``."""

    settings = get_settings()
    model = _resolve_model(settings, role, tier)
    return _cached_model(settings.llm_provider, model)
