"""Thin OpenAI wrapper with a deterministic offline fallback.

When ``OPENAI_API_KEY`` is unset the wrapper returns a small mock JSON payload
so the full agent pipeline still runs end-to-end during local development and
tests. Each agent passes a ``mock`` callable describing what to return offline.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from .config import Settings, get_settings


class LLMClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = None
        if self.settings.llm_enabled:
            from openai import OpenAI  # imported lazily so tests run without it

            self._client = OpenAI(api_key=self.settings.openai_api_key)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        mock: Callable[[], dict[str, Any]],
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Run a chat completion constrained to a JSON object.

        Falls back to ``mock()`` when no API key is configured or the call
        fails to return valid JSON.
        """
        if not self.enabled:
            return mock()

        try:
            resp = self._client.chat.completions.create(
                model=self.settings.openai_model,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            content = resp.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception:
            # Never let an LLM hiccup take down the pipeline; degrade to mock.
            return mock()
