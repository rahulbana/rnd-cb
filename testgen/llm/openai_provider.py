"""OpenAI (and OpenAI-compatible) chat-completion backend."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .base import LLMError, LLMProvider


@dataclass
class OpenAIProvider(LLMProvider):
    """Talks to the OpenAI Chat Completions API.

    Also works with any OpenAI-compatible endpoint by setting ``base_url``
    (e.g. Azure OpenAI, OpenRouter, or a local vLLM server).
    """

    api_key: str | None = None
    base_url: str | None = None

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = self.base_url or os.environ.get("OPENAI_BASE_URL")
        if not self.api_key:
            raise LLMError(
                "No OpenAI API key found. Set OPENAI_API_KEY or pass --api-key "
                "(or use --provider ollama for a local model)."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise LLMError(
                "The 'openai' package is required for the OpenAI provider. "
                "Install it with: pip install openai"
            ) from exc

        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                timeout=self.timeout,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:  # pragma: no cover - network/runtime guard
            raise LLMError(f"OpenAI request failed: {exc}") from exc

        content = resp.choices[0].message.content
        if not content:
            raise LLMError("OpenAI returned an empty response.")
        return content
