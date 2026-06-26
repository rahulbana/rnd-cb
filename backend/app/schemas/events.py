"""Typed definitions for the progress events streamed to the client.

The wire format is intentionally simple (``{"type": <str>, "ts": <float>, ...}``)
so the frontend can consume it without a schema, but defining the event types as
an enum here keeps producers and consumers in sync.
"""
from __future__ import annotations

from enum import Enum


class EventType(str, Enum):
    RUN_START = "run_start"
    NODE_START = "node_start"
    NODE_END = "node_end"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TOOL_ERROR = "tool_error"
    SUBQUERIES = "subqueries"
    SOURCE = "source"
    TOKEN = "token"
    REPORT = "report"
    STATS = "stats"
    DONE = "done"
    ERROR = "error"
