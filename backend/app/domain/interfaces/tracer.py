"""Tracer port -- structured spans across API, worker, and vector store."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.core.config import Settings


@runtime_checkable
class Tracer(Protocol):
    """Any tracing backend (OpenTelemetry, Langfuse, noop) must satisfy this."""

    name: str  # "noop" | "otel" | ...

    @classmethod
    def from_settings(cls, settings: Settings) -> Tracer:
        """Construct the adapter from application settings."""
        ...

    def span(self, name: str, **attributes: Any) -> AbstractContextManager[Any]:
        """Open a span as a context manager, tagged with attributes."""
        ...
