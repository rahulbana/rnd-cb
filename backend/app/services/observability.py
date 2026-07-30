"""Langfuse observability: trace requests, LLM calls and tools used.

Everything here degrades to a no-op when Langfuse is not installed or not
configured (no keys), so the app runs identically without it. When both
LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set, the OpenAI client is
auto-instrumented and each request is wrapped in a trace with nested spans
for the tools it used (RAG, style refs, web research, duplicate detection).
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = None
_enabled = False


def configure() -> None:
    """Initialise Langfuse if keys are present. Safe to call once at startup."""
    global _client, _enabled
    if not (
        settings.LANGFUSE_ENABLED
        and settings.LANGFUSE_PUBLIC_KEY
        and settings.LANGFUSE_SECRET_KEY
    ):
        logger.info("Langfuse tracing disabled (no keys configured).")
        return
    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
        _enabled = True
        logger.info("Langfuse tracing enabled (host=%s).", settings.LANGFUSE_HOST)
    except Exception as exc:  # pragma: no cover
        logger.warning("Langfuse init failed (%s); tracing disabled.", exc)


def is_enabled() -> bool:
    return _enabled


def get_openai_client(**kwargs):
    """Return an OpenAI client, instrumented by Langfuse when enabled."""
    if _enabled:
        try:
            from langfuse.openai import OpenAI as InstrumentedOpenAI

            return InstrumentedOpenAI(**kwargs)
        except Exception as exc:  # pragma: no cover
            logger.warning("Langfuse OpenAI wrapper unavailable (%s).", exc)
    from openai import OpenAI

    return OpenAI(**kwargs)


class _NoopSpan:
    def update(self, **_: Any) -> None:  # noqa: D401
        pass

    def update_trace(self, **_: Any) -> None:
        pass


@contextmanager
def span(name: str, *, input: Any = None, metadata: dict | None = None):
    """Context manager for a (possibly nested) trace span. No-op when disabled.

    Only span *creation* is guarded; exceptions raised inside the ``with``
    body propagate normally (the span records the error and closes). The
    generator yields exactly once on every path.
    """
    if not _enabled or _client is None:
        yield _NoopSpan()
        return
    try:
        cm = _client.start_as_current_span(name=name, input=input, metadata=metadata)
    except Exception as exc:  # pragma: no cover - never break the request
        logger.debug("Langfuse span '%s' create error: %s", name, exc)
        yield _NoopSpan()
        return
    with cm as s:
        yield s


def set_trace(**kwargs: Any) -> None:
    """Attach attributes (user_id, session_id, tags, input, output, metadata)
    to the current trace."""
    if not _enabled or _client is None:
        return
    try:
        _client.update_current_trace(**kwargs)
    except Exception as exc:  # pragma: no cover
        logger.debug("Langfuse update_current_trace error: %s", exc)


def current_trace_id() -> str | None:
    """The active trace id (call inside a span). None when disabled."""
    if not _enabled or _client is None:
        return None
    try:
        return _client.get_current_trace_id()
    except Exception:  # pragma: no cover
        return None


def score(
    *,
    trace_id: str,
    name: str,
    value: float | str,
    data_type: str | None = None,
    comment: str | None = None,
    session_id: str | None = None,
    metadata: dict | None = None,
) -> bool:
    """Attach a score/feedback signal to a trace. No-op when disabled."""
    if not _enabled or _client is None or not trace_id:
        return False
    try:
        _client.create_score(
            trace_id=trace_id,
            name=name,
            value=value,
            data_type=data_type,
            comment=comment,
            session_id=session_id,
            metadata=metadata,
        )
        return True
    except Exception as exc:  # pragma: no cover
        logger.debug("Langfuse score '%s' error: %s", name, exc)
        return False


def flush() -> None:
    if _enabled and _client is not None:
        try:
            _client.flush()
        except Exception:  # pragma: no cover
            pass
