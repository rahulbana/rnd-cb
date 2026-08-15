"""Parser interface and a small helper for lazy optional-dependency imports."""
from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from typing import Any

from ..models import ParsedDocument


class ParserError(RuntimeError):
    pass


def require(module: str, extra_hint: str | None = None) -> Any:
    """Import an optional heavy dependency lazily, with a clear message.

    Keeping these imports out of module top-level lets the API boot even when
    a particular backend's libraries aren't installed, and only fail loudly if
    that specific parser is actually invoked.
    """
    try:
        return importlib.import_module(module)
    except ImportError as exc:  # pragma: no cover - environment dependent
        hint = f" Install with: pip install {extra_hint}" if extra_hint else ""
        raise ParserError(
            f"Required library '{module}' is not installed.{hint}"
        ) from exc


class BaseParser(ABC):
    """Turns raw bytes of one file into a normalized ParsedDocument."""

    name: str = "base"

    @abstractmethod
    def parse(self, path: str, source_name: str) -> ParsedDocument:
        ...
