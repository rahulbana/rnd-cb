"""Thin wrapper around the OpenAI client, shared by the agent and LLM tools."""
from __future__ import annotations

from functools import lru_cache

from ..config import config


class LLMUnavailable(RuntimeError):
    """Raised when an LLM call is attempted without a configured API key."""


@lru_cache(maxsize=1)
def get_client():
    """Return a cached OpenAI client, or raise LLMUnavailable if no key is set."""
    if not config.has_openai():
        raise LLMUnavailable(
            "OPENAI_API_KEY is not configured. Add it to your .env file to enable "
            "LLM-powered features (chat, translate, summarize, fact-check)."
        )
    from openai import OpenAI

    return OpenAI(api_key=config.OPENAI_API_KEY)


def complete(system: str, user: str, *, temperature: float = 0.2,
             max_tokens: int = 1200, model: str | None = None) -> str:
    """Single-shot chat completion returning the assistant's text."""
    client = get_client()
    resp = client.chat.completions.create(
        model=model or config.OPENAI_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (resp.choices[0].message.content or "").strip()
