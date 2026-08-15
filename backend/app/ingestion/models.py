"""Normalized document model produced by every parser.

Regardless of source format, parsers emit a list of ``Element`` objects. An
element is a semantically meaningful unit (paragraph, table, title, ocr block)
with text and provenance metadata. Downstream chunking operates on elements so
it never blindly merges, say, a table row into surrounding prose.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ElementType(str, Enum):
    TITLE = "title"
    TEXT = "text"
    TABLE = "table"
    LIST = "list"
    OCR = "ocr"
    CAPTION = "caption"
    ROW = "row"  # a single CSV/Excel record


class Element(BaseModel):
    type: ElementType = ElementType.TEXT
    text: str
    # Free-form provenance: page number, sheet name, slide index, etc.
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    source_name: str
    mime_type: str | None = None
    parser: str  # which backend produced this
    elements: list[Element] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def text(self) -> str:
        return "\n\n".join(e.text for e in self.elements if e.text.strip())
