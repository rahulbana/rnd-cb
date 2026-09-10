"""OpenAI client (lazily constructed) and local token counting."""

from __future__ import annotations

import tiktoken
from openai import AsyncOpenAI

from .config import config

MODEL = config.model

# A single lazily-constructed async client. The zero-arg constructor reads
# OPENAI_API_KEY from the environment (set OPENAI_BASE_URL to target a compatible
# endpoint). We build it lazily so the server can still boot, serve the UI, and
# count tokens without a key; only real API calls then fail, with a clear error.
_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client


# The OpenAI API has no pre-send token-count endpoint, so we count locally with
# tiktoken. Resolve the encoding once; fall back to o200k_base (used by the
# gpt-4o / gpt-4.1 families) for models tiktoken doesn't recognize, and to a crude
# character heuristic if the encoding data can't be loaded (e.g. offline).
try:
    _encoding = tiktoken.encoding_for_model(MODEL)
except KeyError:
    _encoding = tiktoken.get_encoding("o200k_base")
except Exception:  # pragma: no cover - encoding data unavailable
    _encoding = None


def count_tokens(system: str, user_content: str) -> int:
    """Estimate the input tokens a request would consume, before sending it.

    This is the heart of "context handling": it lets us decide between a single
    pass and a chunked map-reduce, and lets the UI show real numbers. It counts
    prompt text only (ignoring the small per-message chat overhead), so treat it
    as a close estimate rather than exact billing.
    """
    if _encoding is None:
        return (len(system) + len(user_content)) // 4
    return len(_encoding.encode(system)) + len(_encoding.encode(user_content))
