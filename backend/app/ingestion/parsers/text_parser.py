"""Plain text / markdown / raw-string parser."""
from __future__ import annotations

from ..models import Element, ElementType, ParsedDocument
from .base import BaseParser


class TextParser(BaseParser):
    name = "text"

    def parse(self, path: str, source_name: str) -> ParsedDocument:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        return self.from_string(content, source_name)

    def from_string(self, content: str, source_name: str) -> ParsedDocument:
        elements: list[Element] = []
        # Split on blank lines into paragraph-ish blocks; keeps structure that
        # the recursive chunker can later group by token budget.
        for block in content.split("\n\n"):
            block = block.strip()
            if not block:
                continue
            etype = ElementType.TITLE if _looks_like_heading(block) else ElementType.TEXT
            elements.append(Element(type=etype, text=block))
        if not elements and content.strip():
            elements.append(Element(type=ElementType.TEXT, text=content.strip()))
        return ParsedDocument(
            source_name=source_name, parser=self.name, elements=elements
        )


def _looks_like_heading(block: str) -> bool:
    if "\n" in block:
        return False
    return block.startswith("#") or (len(block) < 80 and block.isupper())
