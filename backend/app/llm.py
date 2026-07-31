"""OpenAI + Langfuse integration.

All LLM calls (chat completions, embeddings, memory extraction) go through
this module so they can be traced in Langfuse. A single Langfuse trace is
created per chat request and tied to the user id and session id.
"""

from __future__ import annotations

import logging

from openai import OpenAI

from .config import settings

logger = logging.getLogger(__name__)

# ---- OpenAI client ----
_openai_client: OpenAI | None = None


def get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured. Set it in backend/.env"
            )
        _openai_client = OpenAI(api_key=settings.openai_api_key)
    return _openai_client


# ---- Langfuse client (optional / graceful) ----
_langfuse_client = None
_langfuse_ready = False


def get_langfuse():
    """Return a Langfuse client, or None if not configured/available."""
    global _langfuse_client, _langfuse_ready
    if _langfuse_ready:
        return _langfuse_client

    _langfuse_ready = True
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        logger.info("Langfuse not configured; tracing disabled.")
        return None
    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        logger.info("Langfuse tracing enabled.")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to init Langfuse: %s", exc)
        _langfuse_client = None
    return _langfuse_client


def chat_completion(
    messages: list[dict],
    *,
    trace=None,
    generation_name: str = "chat",
    metadata: dict | None = None,
) -> str:
    """Call OpenAI chat completions, tracing the generation in Langfuse."""
    client = get_openai()
    model = settings.openai_model

    generation = None
    if trace is not None:
        try:
            generation = trace.generation(
                name=generation_name,
                model=model,
                input=messages,
                metadata=metadata,
            )
        except Exception as exc:  # pragma: no cover
            logger.debug("Langfuse generation start failed: %s", exc)

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
    )
    reply = response.choices[0].message.content or ""

    if generation is not None:
        try:
            usage = response.usage
            generation.end(
                output=reply,
                usage={
                    "input": usage.prompt_tokens,
                    "output": usage.completion_tokens,
                    "total": usage.total_tokens,
                }
                if usage
                else None,
            )
        except Exception as exc:  # pragma: no cover
            logger.debug("Langfuse generation end failed: %s", exc)

    return reply


def embed(text: str, *, trace=None) -> list[float] | None:
    """Return an embedding vector for `text`, or None on failure."""
    try:
        client = get_openai()
        span = None
        if trace is not None:
            try:
                span = trace.span(name="embedding", input=text)
            except Exception:
                span = None
        resp = client.embeddings.create(
            model=settings.openai_embedding_model, input=text
        )
        vector = resp.data[0].embedding
        if span is not None:
            try:
                span.end(output={"dimensions": len(vector)})
            except Exception:
                pass
        return vector
    except Exception as exc:  # pragma: no cover
        logger.warning("Embedding failed: %s", exc)
        return None
