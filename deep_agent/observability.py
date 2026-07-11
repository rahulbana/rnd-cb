"""Langfuse tracing / observability integration.

Provides an optional LangChain ``CallbackHandler`` that traces every LLM
call and graph node to Langfuse.  Tracing is off by default and enabled via
``LANGFUSE_ENABLED`` + credentials, so the tool runs fine without Langfuse
installed or configured.

The handler is passed through the LangGraph run config; LangChain then
propagates it to the LLM calls inside each agent automatically.
"""
from __future__ import annotations

import os
from typing import Any

from deep_agent.config import get_settings
from deep_agent.utils.logging import get_logger

logger = get_logger("observability")


def _export_credentials() -> None:
    """Mirror settings into the env vars the Langfuse SDK reads."""

    settings = get_settings()
    if settings.langfuse_public_key:
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    if settings.langfuse_secret_key:
        os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)


def get_langfuse_handler() -> Any | None:
    """Return a Langfuse LangChain callback handler, or ``None`` if disabled.

    Tolerant of both the v3 (``langfuse.langchain``) and v2
    (``langfuse.callback``) SDK layouts.
    """

    settings = get_settings()
    if not settings.langfuse_enabled:
        return None

    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        logger.warning(
            "Langfuse enabled but LANGFUSE_PUBLIC_KEY/SECRET_KEY missing; "
            "tracing disabled."
        )
        return None

    _export_credentials()

    # v3 SDK: reads credentials from the environment.
    try:
        from langfuse.langchain import CallbackHandler

        logger.info("Langfuse tracing enabled (host=%s)", settings.langfuse_host)
        return CallbackHandler()
    except ImportError:
        pass

    # v2 SDK: credentials passed explicitly.
    try:
        from langfuse.callback import CallbackHandler

        logger.info("Langfuse tracing enabled (host=%s, v2)", settings.langfuse_host)
        return CallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except ImportError as exc:
        logger.warning(
            "Langfuse enabled but its LangChain integration is unavailable "
            "(%s); ensure 'langfuse' and 'langchain' are installed. "
            "Tracing disabled.",
            exc,
        )
        return None


def flush_langfuse() -> None:
    """Flush buffered traces — important for short-lived CLI processes."""

    settings = get_settings()
    if not settings.langfuse_enabled:
        return
    try:  # v3
        from langfuse import get_client

        get_client().flush()
        return
    except Exception:  # noqa: BLE001
        pass
    try:  # v2
        from langfuse import Langfuse

        Langfuse().flush()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Langfuse flush skipped: %s", exc)
