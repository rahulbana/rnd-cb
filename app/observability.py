"""Langfuse observability wiring.

`get_langfuse_handler()` returns a LangChain callback handler when Langfuse
credentials are configured, else `None`. Nodes and the graph pass it through
`config={"callbacks": [...]}` so every LLM/tool span is traced with the job id
as the trace name. When Langfuse isn't configured the app runs unchanged.
"""

from __future__ import annotations

import logging

from app.config import Settings

logger = logging.getLogger(__name__)


def get_langfuse_handler(settings: Settings, *, job_id: str, topic: str):
    if not settings.has_langfuse:
        return None
    try:
        from langfuse.callback import CallbackHandler

        return CallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            trace_name=f"research:{job_id}",
            metadata={"topic": topic, "job_id": job_id},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Langfuse handler unavailable: %s", exc)
        return None
