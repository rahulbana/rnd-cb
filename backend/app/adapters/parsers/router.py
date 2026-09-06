"""MIME-based parser router with a fallback chain.

Picks parsers by MIME type in a configured priority order and tries them in
turn. A parser that raises (missing optional dependency, malformed input) is
skipped and the next candidate runs. Fallbacks are **logged and recorded on
the result** (``used_fallback``), never silent -- a quiet drop from Docling to
a weaker parser is exactly the failure mode Phase 2 must surface.

The router itself satisfies the ``Parser`` port, so ``get_parser()`` can return
it and the ingestion service depends on the port, not on routing details.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.domain.models import ParsedDocument

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.domain.interfaces import Parser

logger = get_logger("parser.router")


class ParserError(RuntimeError):
    """Raised when no parser in the chain could handle a document."""


class ParserRouter:
    """Routes a document to the first working parser that supports its MIME."""

    name = "router"

    def __init__(self, parsers: list[Parser]) -> None:
        # Priority order: earlier parsers are preferred.
        self._parsers = parsers

    @classmethod
    def from_settings(cls, settings: Settings) -> ParserRouter:
        # Imported here to avoid a circular import with the registry.
        from app.core.registry import build_parser_chain

        return cls(build_parser_chain(settings))

    def supports(self, mime_type: str) -> bool:
        return any(p.supports(mime_type) for p in self._parsers)

    def chain_for(self, mime_type: str) -> list[Parser]:
        """The ordered fallback chain of parsers that support ``mime_type``."""
        return [p for p in self._parsers if p.supports(mime_type)]

    async def parse(
        self, data: bytes, *, filename: str, mime_type: str
    ) -> ParsedDocument:
        chain = self.chain_for(mime_type)
        if not chain:
            raise ParserError(
                f"No parser registered for MIME type {mime_type!r} ({filename})."
            )

        errors: list[str] = []
        for index, parser in enumerate(chain):
            try:
                parsed = await parser.parse(data, filename=filename, mime_type=mime_type)
            except Exception as exc:  # noqa: BLE001 - fallbacks are deliberate
                errors.append(f"{parser.name}: {exc}")
                logger.warning(
                    "parser_fallback",
                    filename=filename,
                    mime_type=mime_type,
                    failed_parser=parser.name,
                    error=str(exc),
                )
                continue

            if index > 0:
                parsed.used_fallback = True
                logger.info(
                    "parser_used_fallback",
                    filename=filename,
                    mime_type=mime_type,
                    used_parser=parser.name,
                    skipped=[p.name for p in chain[:index]],
                )
            return parsed

        raise ParserError(
            f"All parsers failed for {filename} ({mime_type}): {'; '.join(errors)}"
        )
