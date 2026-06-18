"""Thin wrapper around the OpenAI client.

Centralising the client here keeps the agents free of SDK boilerplate and gives
us one place to add retries, logging, or model routing later. Two primitives
are exposed:

* :meth:`LLMClient.parse` — structured output into a Pydantic model.
* :meth:`LLMClient.search` — a web-search-enabled call that also returns
  structured output.

The wrapper is resilient to the installed ``openai`` SDK version: it prefers the
modern Responses API (needed for the built-in web-search tool) but falls back to
the Chat Completions API for structured parsing on older SDKs.
"""

from __future__ import annotations

import json
from typing import Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from .config import Settings

T = TypeVar("T", bound=BaseModel)

_UPGRADE_HINT = (
    "Your installed 'openai' package is too old for this feature. "
    "Upgrade with:  pip install -U 'openai>=1.40'"
)


class LLMClient:
    """Convenience facade over the OpenAI APIs (Responses, with fallbacks)."""

    def __init__(self, settings: Settings) -> None:
        settings.require_api_key()
        self._settings = settings
        self._client = OpenAI(api_key=settings.openai_api_key)
        # Feature detection: the Responses API (and its web_search tool) only
        # exists on newer SDKs.
        self._has_responses = hasattr(self._client, "responses")

    # -- structured output ----------------------------------------------------

    def parse(
        self,
        *,
        system: str,
        user: str,
        schema: Type[T],
        model: str | None = None,
    ) -> T:
        """Ask the model to respond strictly in the shape of ``schema``."""
        model = model or self._settings.model
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        if self._has_responses:
            response = self._client.responses.parse(
                model=model, input=messages, text_format=schema
            )
            parsed = response.output_parsed
            if parsed is None:  # pragma: no cover - defensive.
                raise RuntimeError("Model returned no parseable structured output.")
            return parsed

        return self._parse_chat(model=model, messages=messages, schema=schema)

    def _parse_chat(self, *, model: str, messages: list, schema: Type[T]) -> T:
        """Structured output via the Chat Completions API (older SDKs)."""
        # Preferred: the beta `.parse` helper understands Pydantic models.
        beta = getattr(self._client, "beta", None)
        if beta is not None and hasattr(beta, "chat"):
            try:
                completion = beta.chat.completions.parse(
                    model=model, messages=messages, response_format=schema
                )
                parsed = completion.choices[0].message.parsed
                if parsed is not None:
                    return parsed
            except Exception:
                # Fall through to JSON-mode parsing below.
                pass

        # Last resort: ask for raw JSON and validate it ourselves.
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        json_messages = list(messages)
        json_messages[-1] = {
            "role": "user",
            "content": (
                f"{messages[-1]['content']}\n\n"
                "Respond with a single JSON object that conforms to this JSON "
                f"schema. Output JSON only, no prose:\n{schema_json}"
            ),
        }
        completion = self._client.chat.completions.create(
            model=model,
            messages=json_messages,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content or "{}"
        return schema.model_validate_json(content)

    # -- web-search-augmented retrieval ---------------------------------------

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
        if not self._has_responses:
            raise RuntimeError(
                "Web search requires the OpenAI Responses API. " + _UPGRADE_HINT
            )

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
