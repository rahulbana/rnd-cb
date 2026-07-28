"""LLM access layer built on langchain-anthropic.

Centralizes model construction so nodes ask for a *role* ("fast" vs "smart")
rather than a model id, and so token usage is uniformly extractable for the
budget tracker. `structured` returns a runnable that emits a validated Pydantic
object via Anthropic tool-use, which is how the synthesis node produces a
`ResearchReport`.
"""

from __future__ import annotations

from typing import TypeVar

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage
from pydantic import BaseModel

from app.budget import Usage
from app.config import Settings

T = TypeVar("T", bound=BaseModel)


class LLM:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _model_id(self, role: str) -> str:
        return self._settings.smart_model if role == "smart" else self._settings.fast_model

    def chat(self, role: str = "fast", *, temperature: float = 0.2) -> ChatAnthropic:
        return ChatAnthropic(
            model=self._model_id(role),
            temperature=temperature,
            api_key=self._settings.anthropic_api_key,
            max_tokens=4096,
        )

    def structured(self, schema: type[T], *, role: str = "smart"):
        """Return a runnable that emits `schema` and the raw message (for usage)."""
        return self.chat(role).with_structured_output(schema, include_raw=True)

    @staticmethod
    def usage_from(message: BaseMessage, model: str) -> Usage:
        """Extract token usage from an Anthropic AIMessage."""
        meta: dict = {}
        if isinstance(message, AIMessage):
            meta = message.usage_metadata or {}  # type: ignore[assignment]
        return Usage(
            input_tokens=int(meta.get("input_tokens", 0)) if meta else 0,
            output_tokens=int(meta.get("output_tokens", 0)) if meta else 0,
            model=model,
        )
