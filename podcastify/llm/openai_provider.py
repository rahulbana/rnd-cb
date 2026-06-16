"""OpenAI implementation of :class:`LLMProvider` (the default)."""

from __future__ import annotations

import os
from typing import List, Optional, Type, TypeVar

from pydantic import BaseModel

from .base import LLMProvider, Message

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        client=None,
    ) -> None:
        self.model = model
        if client is not None:
            self.client = client
            return
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError(
                "OpenAI API key missing. Set OPENAI_API_KEY or pass api_key."
            )
        from openai import OpenAI

        self.client = OpenAI(api_key=key)

    def complete(self, messages: List[Message], temperature: float = 0.7) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=list(messages),
        )
        return (resp.choices[0].message.content or "").strip()

    def complete_structured(
        self,
        messages: List[Message],
        schema: Type[T],
        temperature: float = 0.7,
    ) -> T:
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            temperature=temperature,
            messages=list(messages),
            response_format=schema,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:  # pragma: no cover - defensive
            raise RuntimeError("OpenAI returned no parseable structured output")
        return parsed
