"""Thin OpenAI wrapper with JSON-mode helpers.

Agents talk to the model exclusively through :class:`LLMClient` so that
prompting conventions, retries and structured-output parsing live in one
place. Swapping providers later means reimplementing this single module.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from .config import Settings

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Stateless helper around the OpenAI Chat Completions API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAI(api_key=settings.require_openai())

    # -- Plain text --------------------------------------------------------
    def complete(
        self,
        system: str,
        user: str,
        *,
        fast: bool = False,
        temperature: Optional[float] = None,
    ) -> str:
        """Return a free-form text completion."""
        resp = self._client.chat.completions.create(
            model=self._settings.fast_model if fast else self._settings.model,
            temperature=self._settings.temperature if temperature is None else temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip()

    # -- Structured JSON ---------------------------------------------------
    def complete_json(
        self,
        system: str,
        user: str,
        *,
        fast: bool = False,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Return parsed JSON using the model's JSON response mode."""
        resp = self._client.chat.completions.create(
            model=self._settings.fast_model if fast else self._settings.model,
            temperature=self._settings.temperature if temperature is None else temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        raw = resp.choices[0].message.content or "{}"
        return json.loads(raw)

    def complete_model(
        self,
        schema: Type[T],
        system: str,
        user: str,
        *,
        fast: bool = False,
        temperature: Optional[float] = None,
    ) -> T:
        """Return JSON validated into a Pydantic model.

        The target schema is injected into the system prompt so the model
        knows the exact shape to emit.
        """
        schema_hint = json.dumps(schema.model_json_schema(), indent=2)
        system_with_schema = (
            f"{system}\n\nRespond with a single JSON object matching this "
            f"JSON Schema (no markdown, no commentary):\n{schema_hint}"
        )
        data = self.complete_json(
            system_with_schema, user, fast=fast, temperature=temperature
        )
        try:
            return schema.model_validate(data)
        except ValidationError as exc:  # pragma: no cover - defensive
            raise ValueError(
                f"Model returned JSON that did not match {schema.__name__}: {exc}"
            ) from exc
