"""Natural-language -> validated JSON generation via OpenAI.

The strategy here is what most production GenAI systems converge on:

1. Ask the model for JSON (using JSON mode so the response is always parseable).
2. Parse it. If parsing fails, feed the error back and retry.
3. If a JSON Schema was supplied, validate against it.
4. On validation failure, feed the specific errors back to the model and ask
   it to correct the output. Repeat up to ``max_correction_attempts`` times.

This "generate -> validate -> correct" loop is what makes structured LLM
output reliable enough to ship.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from .config import Settings
from .validator import validate


class GenerationError(RuntimeError):
    """Raised when generation cannot proceed (e.g. missing API key)."""


@dataclass
class GenerationResult:
    """Outcome of a generation run."""

    data: Any | None
    valid: bool
    attempts: int
    errors: list[dict[str, str]] = field(default_factory=list)
    raw_output: str | None = None


_SYSTEM_PROMPT = (
    "You are a precise data-extraction engine. Convert the user's natural-"
    "language description into a single valid JSON value. Respond with JSON "
    "only — no prose, no markdown, no code fences. Infer sensible types: use "
    "numbers for numeric quantities, booleans for yes/no, and arrays for "
    "lists. Only include fields that are stated or clearly implied."
)


def _build_generation_messages(
    prompt: str, schema: dict[str, Any] | None
) -> list[dict[str, str]]:
    """Assemble the initial chat messages for a generation request."""
    user_content = f"Description:\n{prompt.strip()}"
    if schema is not None:
        user_content += (
            "\n\nThe JSON you produce MUST conform to this JSON Schema:\n"
            + json.dumps(schema, indent=2)
        )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def _build_correction_message(errors: list[dict[str, str]]) -> dict[str, str]:
    """Build a user message describing validation errors to fix."""
    lines = [f"- at {err['path']}: {err['message']}" for err in errors]
    return {
        "role": "user",
        "content": (
            "The JSON you returned failed schema validation with these "
            "errors:\n"
            + "\n".join(lines)
            + "\n\nReturn a corrected JSON value that fixes every error. "
            "Respond with JSON only."
        ),
    }


class JSONGenerator:
    """Generates validated JSON from natural language using an LLM."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if not self._settings.is_configured:
            raise GenerationError(
                "OPENAI_API_KEY is not set. Add it to backend/.env "
                "(see .env.example)."
            )
        if self._client is None:
            self._client = OpenAI(
                api_key=self._settings.openai_api_key,
                base_url=self._settings.openai_base_url,
            )
        return self._client

    def _call_model(self, messages: list[dict[str, str]]) -> str:
        response = self.client.chat.completions.create(
            model=self._settings.model,
            temperature=self._settings.temperature,
            response_format={"type": "json_object"},
            messages=messages,
        )
        return response.choices[0].message.content or ""

    def generate(
        self, prompt: str, schema: dict[str, Any] | None = None
    ) -> GenerationResult:
        """Run the generate -> validate -> correct loop."""
        messages = _build_generation_messages(prompt, schema)
        raw = ""
        data: Any = None
        errors: list[dict[str, str]] = []

        # attempt 0 = initial generation; each extra iteration is a correction.
        max_attempts = 1 + max(0, self._settings.max_correction_attempts)

        for attempt in range(1, max_attempts + 1):
            raw = self._call_model(messages)

            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                # Model returned non-JSON: ask it to fix and try again.
                errors = [{"path": "(root)", "message": f"Invalid JSON: {exc}"}]
                if attempt == max_attempts:
                    break
                messages.append({"role": "assistant", "content": raw})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "That was not valid JSON. Return a single valid "
                            "JSON value only."
                        ),
                    }
                )
                continue

            if schema is None:
                # No schema to check against -> whatever parsed is accepted.
                return GenerationResult(
                    data=data, valid=True, attempts=attempt, raw_output=raw
                )

            errors = validate(data, schema)
            if not errors:
                return GenerationResult(
                    data=data, valid=True, attempts=attempt, raw_output=raw
                )

            if attempt == max_attempts:
                break

            # Feed the validation errors back for correction.
            messages.append({"role": "assistant", "content": raw})
            messages.append(_build_correction_message(errors))

        return GenerationResult(
            data=data,
            valid=False,
            attempts=max_attempts,
            errors=errors,
            raw_output=raw,
        )
