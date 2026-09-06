"""No-op tracer -- spans do nothing. Default in dev/tests."""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.core.config import Settings


class NoopTracer:
    """A tracer whose spans are no-ops."""

    name = "noop"

    @classmethod
    def from_settings(cls, settings: Settings) -> NoopTracer:
        return cls()

    def span(self, name: str, **attributes: Any) -> AbstractContextManager[Any]:
        return nullcontext()
