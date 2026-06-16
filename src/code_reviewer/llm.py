"""Thin wrapper around the OpenAI client with JSON-structured output."""

from __future__ import annotations

import json
from typing import List

from openai import OpenAI

# JSON schema the model must conform to. Using structured output keeps the
# response parseable instead of relying on free-form text.
_RESPONSE_SCHEMA = {
    "name": "code_review",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "summary": {
                "type": "string",
                "description": "One or two sentence overview for this category.",
            },
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "severity": {
                            "type": "string",
                            "enum": [
                                "critical",
                                "high",
                                "medium",
                                "low",
                                "info",
                            ],
                        },
                        "line": {
                            "type": ["integer", "null"],
                            "description": "Approximate line number, or null.",
                        },
                        "description": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                    "required": [
                        "title",
                        "severity",
                        "line",
                        "description",
                        "recommendation",
                    ],
                },
            },
        },
        "required": ["summary", "findings"],
    },
}


class LLMError(RuntimeError):
    """Raised when the LLM call fails or returns unparseable output."""


class LLMClient:
    """Wraps OpenAI chat completions with a fixed review schema."""

    def __init__(self, model: str, client: OpenAI | None = None):
        self.model = model
        # Client reads OPENAI_API_KEY from the environment by default.
        self._client = client or OpenAI()

    def review(self, system_prompt: str, user_prompt: str) -> dict:
        """Run one structured review call and return the parsed JSON dict."""
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": _RESPONSE_SCHEMA,
                },
                temperature=0,
            )
        except Exception as exc:  # noqa: BLE001 - surface any SDK/HTTP error
            raise LLMError(str(exc)) from exc

        content = response.choices[0].message.content or "{}"
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"Model returned invalid JSON: {exc}") from exc


def number_lines(source: str) -> str:
    """Prefix each line with its number so the model can cite locations."""
    lines: List[str] = source.splitlines()
    width = len(str(len(lines))) if lines else 1
    return "\n".join(
        f"{str(i).rjust(width)}| {line}" for i, line in enumerate(lines, start=1)
    )
