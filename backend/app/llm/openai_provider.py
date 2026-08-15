"""OpenAI (and OpenAI-compatible) chat provider with streaming."""
from __future__ import annotations

from typing import AsyncIterator

from .base import BaseLLM, Message
from ..config import get_settings


class OpenAILLM(BaseLLM):
    name = "openai"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY (RAG_OPENAI_API_KEY) is not set. Set it, or switch "
                "RAG_LLM_PROVIDER=ollama for a local model."
            )
        from openai import AsyncOpenAI

        self.model = settings.llm_model
        self._temperature = settings.llm_temperature
        self._max_tokens = settings.llm_max_tokens
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
        )

    async def stream(self, messages: list[Message]) -> AsyncIterator[str]:
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            stream=True,
        )
        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
