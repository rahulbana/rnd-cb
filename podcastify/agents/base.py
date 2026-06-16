"""Base class for the LLM-powered agents.

Agents depend on the vendor-neutral :class:`~podcastify.llm.LLMProvider`
interface rather than any specific SDK, so the model backend can be swapped
without changing agent code. Each agent sets ``name`` and ``system_prompt``
and calls :meth:`complete` (free text) or :meth:`complete_structured`
(parsed into a Pydantic model).
"""

from __future__ import annotations

import logging
from typing import Type, TypeVar

from pydantic import BaseModel

from ..llm import LLMProvider, Message

logger = logging.getLogger("podcastify")

T = TypeVar("T", bound=BaseModel)


class LLMAgent:
    """Common behaviour for an agent backed by an :class:`LLMProvider`."""

    name: str = "agent"
    system_prompt: str = "You are a helpful assistant."

    def __init__(self, provider: LLMProvider, temperature: float = 0.7) -> None:
        self.provider = provider
        self.temperature = temperature

    # -- helpers ------------------------------------------------------------

    def _log(self, message: str) -> None:
        logger.info("[%s] %s", self.name, message)

    def _messages(self, user_prompt: str) -> list[Message]:
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def complete(self, user_prompt: str) -> str:
        """Return a plain-text completion."""
        self._log(f"calling LLM (text) via {self.provider.name}:{self.provider.model}")
        return self.provider.complete(
            self._messages(user_prompt), temperature=self.temperature
        )

    def complete_structured(self, user_prompt: str, schema: Type[T]) -> T:
        """Return a completion parsed into ``schema`` (a Pydantic model)."""
        self._log(f"calling LLM (structured -> {schema.__name__})")
        return self.provider.complete_structured(
            self._messages(user_prompt), schema, temperature=self.temperature
        )
