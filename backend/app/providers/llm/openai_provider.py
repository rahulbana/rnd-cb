"""OpenAI-backed LLM provider."""
from __future__ import annotations

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from ...core.config import Settings
from ...core.exceptions import ConfigurationError
from .base import BaseLLMProvider


class OpenAILLMProvider(BaseLLMProvider):
    name = "openai"

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is not set. Add it to your environment or .env file."
            )
        self._settings = settings

    def chat_model(
        self, *, streaming: bool = False, max_tokens: Optional[int] = None
    ) -> BaseChatModel:
        return ChatOpenAI(
            model=self._settings.openai_model,
            api_key=self._settings.openai_api_key,
            temperature=self._settings.llm_temperature,
            streaming=streaming,
            max_tokens=max_tokens,
        )
