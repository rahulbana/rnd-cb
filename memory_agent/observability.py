"""Optional Langfuse observability.

Langfuse traces every graph run — LLM calls, tool calls, latencies, token
usage/cost — grouped by user and conversation. It hooks into LangGraph through
a standard LangChain callback handler, so wiring it in is just attaching a
callback and a bit of trace metadata at invoke time.

Everything here is best-effort and fully optional: with no keys configured (or
the package not installed) tracing is silently disabled and the chat behaves
exactly as before. A misconfigured tracer never breaks the conversation.
"""

from __future__ import annotations

import os

from .config import Settings


def build_langfuse_handler(settings: Settings):
    """Return a Langfuse LangChain callback handler, or ``None`` if disabled.

    Supports both Langfuse v3 (``langfuse.langchain``) and v2
    (``langfuse.callback``) import paths.
    """
    if not settings.langfuse_enabled:
        return None

    # The handler / client read credentials from the environment.
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)

    try:
        try:
            from langfuse.langchain import CallbackHandler  # v3
        except ImportError:
            from langfuse.callback import CallbackHandler  # v2
        return CallbackHandler()
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[langfuse] tracing disabled ({exc})")
        return None


def instrument(config: dict, handler, *, user_id: str, session_id: str,
               tags: list[str] | None = None) -> dict:
    """Return a copy of ``config`` with the Langfuse callback and trace metadata.

    ``user_id`` / ``session_id`` become the Langfuse user and session so traces
    are grouped per user and per conversation in the dashboard. If ``handler``
    is ``None`` the config is returned unchanged.
    """
    if handler is None:
        return config
    config = dict(config)
    config["callbacks"] = [handler]
    metadata = dict(config.get("metadata", {}))
    metadata.update(
        {
            "langfuse_user_id": user_id,
            "langfuse_session_id": session_id,
            "langfuse_tags": tags or ["memory-chatbot", "cli"],
        }
    )
    config["metadata"] = metadata
    return config


def flush() -> None:
    """Flush pending Langfuse events (call before exit). Best-effort."""
    try:
        from langfuse import get_client

        get_client().flush()
    except Exception:  # pragma: no cover - v2 or not installed
        pass
