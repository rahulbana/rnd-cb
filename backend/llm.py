"""Thin wrapper around the OpenAI chat completion API."""

from __future__ import annotations

import os

from openai import OpenAI, OpenAIError

_client: OpenAI | None = None


class LLMNotConfigured(RuntimeError):
    """Raised when no API key is available."""


def _get_client() -> OpenAI:
    global _client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMNotConfigured(
            "OPENAI_API_KEY is not set. Copy backend/.env.example to "
            "backend/.env and add your key."
        )
    if _client is None:
        _client = OpenAI(api_key=api_key)
    return _client


def complete(system_prompt: str, user_prompt: str) -> str:
    """Send a two-message chat request and return the text response."""
    client = _get_client()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except OpenAIError as exc:  # network / auth / quota errors
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    content = response.choices[0].message.content
    return (content or "").strip()
