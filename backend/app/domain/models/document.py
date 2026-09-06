"""Canonical parsed-document model.

Every parser adapter returns this same ``ParsedDocument`` regardless of the
source format (PDF, DOCX, PPTX, HTML, images, scanned pages, txt/md).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Coordinates of a block on a page (points, top-left origin)."""

    x0: float
    y0: float
    x1: float
    y1: float


class TextBlock(BaseModel):
    """A run of text with layout metadata."""

    text: str
    page: int | None = None
    heading_path: str | None = None
    bbox: BoundingBox | None = None


class TableBlock(BaseModel):
    """A table extracted from the source, kept structurally."""

    rows: list[list[str]] = Field(default_factory=list)
    page: int | None = None
    caption: str | None = None
    bbox: BoundingBox | None = None


class ParsedDocument(BaseModel):
    """The one shape every parser adapter produces."""

    source_filename: str
    mime_type: str
    text_blocks: list[TextBlock] = Field(default_factory=list)
    tables: list[TableBlock] = Field(default_factory=list)
    image_refs: list[str] = Field(default_factory=list)
    page_count: int = 0
    parser_name: str = ""
    used_fallback: bool = False

    @property
    def full_text(self) -> str:
        """Concatenated text of all blocks, in order."""
        return "\n\n".join(block.text for block in self.text_blocks)
