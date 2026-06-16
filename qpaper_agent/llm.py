"""Thin wrapper around the OpenAI client.

Centralising the client here keeps the agents free of SDK boilerplate and gives
us one place to add retries, logging, or model routing later. Two primitives
are exposed:

* :meth:`LLMClient.parse` — structured output into a Pydantic model.
* :meth:`LLMClient.search` — a web-search-enabled call that also returns
  structured output.
"""

from __future__ import annotations

import json
from typing import Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from .config import Settings

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Convenience facade over the OpenAI Responses API."""

    def __init__(self, settings: Settings) -> None:
        settings.require_api_key()
        self._settings = settings
        self._client = OpenAI(api_key=settings.openai_api_key)

    def parse(
        self,
        *,
        system: str,
        user: str,
        schema: Type[T],
        model: str | None = None,
    ) -> T:
        """Ask the model to respond strictly in the shape of ``schema``."""
        response = self._client.responses.parse(
            model=model or self._settings.model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            text_format=schema,
        )
        parsed = response.output_parsed
        if parsed is None:  # pragma: no cover - defensive.
            raise RuntimeError("Model returned no parseable structured output.")
        return parsed

    def search(
        self,
        *,
        system: str,
        user: str,
        schema: Type[T],
    ) -> T:
        """Run a web-search-augmented request, then coerce to ``schema``.

        The web_search tool cannot be combined with strict structured output in
        a single call, so we do it in two steps: first gather evidence from the
        web, then have the model distil that evidence into the schema.
        """
        research = self._client.responses.create(
            model=self._settings.search_model,
            tools=[{"type": "web_search"}],
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        evidence = research.output_text

        return self.parse(
            system=(
                "You convert raw web-research notes into structured data. "
                "Only include items actually supported by the notes. Never "
                "invent URLs."
            ),
            user=(
                "Web research notes follow. Extract the structured result from "
                "them.\n\n"
                f"Original task:\n{user}\n\n"
                f"Research notes:\n{evidence}"
            ),
            schema=schema,
            model=self._settings.model,
        )

    @staticmethod
    def pretty(model: BaseModel) -> str:
        """Helper for logging a model as indented JSON."""
        return json.dumps(model.model_dump(), indent=2, ensure_ascii=False)
