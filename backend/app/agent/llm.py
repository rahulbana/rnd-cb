"""LLM factory.

Centralizes model construction so retries, timeouts, and model selection are
configured once. Two tiers:
  - `get_worker_llm()`  : cheap, high-frequency calls (plan/extract/reflect)
  - `get_synthesis_llm()`: higher-quality single final-report call
"""
from __future__ import annotations

from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.core.config import get_settings


@lru_cache
def get_worker_llm() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        api_key=settings.openai_api_key,
        max_retries=settings.openai_max_retries,
        timeout=settings.llm_request_timeout,
    )


@lru_cache
def get_synthesis_llm() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_synthesis_model,
        temperature=settings.openai_temperature,
        api_key=settings.openai_api_key,
        max_retries=settings.openai_max_retries,
        timeout=settings.llm_request_timeout,
    )
