"""Base class for the LLM-powered agents.

A thin, dependency-light wrapper around the OpenAI client so every agent
shares the same configuration, logging and structured-output helpers.
"""

from __future__ import annotations

import logging
from typing import Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel

logger = logging.getLogger("podcastify")

T = TypeVar("T", bound=BaseModel)


class LLMAgent:
    """Common behaviour for an agent backed by an OpenAI chat model.

    Each concrete agent sets ``name`` and ``system_prompt`` and then calls
    :meth:`complete` (free text) or :meth:`complete_structured` (parsed into
    a Pydantic model via OpenAI structured outputs).
    """

    name: str = "agent"
    system_prompt: str = "You are a helpful assistant."

    def __init__(
        self,
        client: OpenAI,
        model: str = "gpt-4o",
        temperature: float = 0.7,
    ) -> None:
        self.client = client
        self.model = model
        self.temperature = temperature

    # -- helpers ------------------------------------------------------------

    def _log(self, message: str) -> None:
        logger.info("[%s] %s", self.name, message)

    def complete(self, user_prompt: str) -> str:
        """Return a plain-text completion."""
        self._log("calling LLM (text)")
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return (resp.choices[0].message.content or "").strip()

    def complete_structured(self, user_prompt: str, schema: Type[T]) -> T:
        """Return a completion parsed into ``schema`` (a Pydantic model).

        Uses OpenAI structured outputs so the JSON always matches the schema.
        """
        self._log(f"calling LLM (structured -> {schema.__name__})")
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=schema,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:  # pragma: no cover - defensive
            raise RuntimeError(f"{self.name}: model returned no parseable output")
        return parsed
