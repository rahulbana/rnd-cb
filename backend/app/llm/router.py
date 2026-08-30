"""Model routing and provider selection (spec section 30, cost control).

Cheap models handle classification/extraction; stronger models handle planning
and complex reasoning. Provider selection falls back to the mock provider when
no API key is configured, so the app is always runnable.
"""
from __future__ import annotations

from enum import Enum

from ..config.logging import get_logger
from ..config.settings import get_settings
from .base import LLMProvider
from .mock_provider import MockLLMProvider

logger = get_logger(__name__)


class TaskComplexity(str, Enum):
    SIMPLE = "simple"        # classification, short extraction
    MODERATE = "moderate"    # single-agent research
    COMPLEX = "complex"      # planning, optimisation, synthesis


class ModelRouter:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self._settings = get_settings()
        self._provider = provider or self._build_provider()

    def _build_provider(self) -> LLMProvider:
        if self._settings.llm_enabled:
            try:
                from .openai_provider import OpenAIProvider

                logger.info("LLM provider: OpenAI (%s / %s)",
                            self._settings.llm_model_fast, self._settings.llm_model_strong)
                return OpenAIProvider()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Falling back to mock provider: %s", exc)
        logger.info("LLM provider: mock (offline mode — set OPENAI_API_KEY for full AI)")
        return MockLLMProvider()

    @property
    def provider(self) -> LLMProvider:
        return self._provider

    @property
    def offline(self) -> bool:
        return self._provider.name == "mock"

    def select_model(self, complexity: TaskComplexity) -> str:
        if complexity is TaskComplexity.COMPLEX:
            return self._settings.llm_model_strong
        return self._settings.llm_model_fast
