"""LangGraph checkpointer factory.

A checkpointer persists graph state per ``thread_id`` so runs can be
resumed after a crash and repeated invocations for the same thread are
served from the saved state (de-dupe / caching) instead of recomputing.

Backends (via ``CHECKPOINT_BACKEND``):
* ``none``   — disabled (no thread_id required).
* ``memory`` — in-process only; lost when the process exits.
* ``sqlite`` — persisted to ``CHECKPOINT_DB``; resumable across runs.
"""
from __future__ import annotations

from deep_agent.config import CheckpointBackend, get_settings
from deep_agent.utils.logging import get_logger

logger = get_logger("checkpoint")


def _allowed_schema_modules() -> list[tuple[str, str]]:
    """(module, class) tuples for every schema type we persist in state.

    Registering these lets the serializer reconstruct our Pydantic/enum
    objects on read-back (instead of returning dicts) and keeps SQLite
    checkpointing forward-compatible with LangGraph's stricter msgpack rules.
    """
    import enum
    import inspect

    from pydantic import BaseModel

    from deep_agent.models import schemas

    allowed: list[tuple[str, str]] = []
    for name, obj in inspect.getmembers(schemas, inspect.isclass):
        if obj.__module__ != schemas.__name__:
            continue
        if issubclass(obj, (BaseModel, enum.Enum)):
            allowed.append((schemas.__name__, name))
    return allowed


def get_checkpointer():
    """Return a checkpointer instance for the configured backend, or ``None``."""

    settings = get_settings()
    backend = settings.checkpoint_backend

    if backend is CheckpointBackend.NONE:
        logger.info("Checkpointing disabled.")
        return None

    if backend is CheckpointBackend.SQLITE:
        import sqlite3

        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
        from langgraph.checkpoint.sqlite import SqliteSaver

        # Register our Pydantic schema types so persisted state (which holds
        # ResearchPlan/SearchResult/... objects) is reconstructed as objects
        # on read-back and stays forward-compatible with strict msgpack.
        serde = JsonPlusSerializer(
            allowed_msgpack_modules=_allowed_schema_modules()
        )
        # check_same_thread=False so the saver is usable from Celery/worker
        # threads as well as the main thread.
        conn = sqlite3.connect(settings.checkpoint_db, check_same_thread=False)
        logger.info("Using SQLite checkpointer at %s", settings.checkpoint_db)
        return SqliteSaver(conn, serde=serde)

    from langgraph.checkpoint.memory import MemorySaver

    logger.info("Using in-memory checkpointer.")
    return MemorySaver()
