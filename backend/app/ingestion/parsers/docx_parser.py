"""Word (.docx) parser using python-docx.

Extracts paragraphs (with heading detection from the paragraph style) and
tables (linearized row by row).
"""
from __future__ import annotations

from ..models import Element, ElementType, ParsedDocument
from .base import BaseParser, require


class DocxParser(BaseParser):
    name = "docx"

    def parse(self, path: str, source_name: str) -> ParsedDocument:
        docx = require("docx", "python-docx")
        document = docx.Document(path)
        elements: list[Element] = []

        for para in document.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            style = (para.style.name or "").lower() if para.style else ""
            etype = ElementType.TITLE if style.startswith("heading") or style == "title" \
                else ElementType.TEXT
            elements.append(
                Element(type=etype, text=text, metadata={"style": style})
            )

        for t_idx, table in enumerate(document.tables):
            header = [c.text.strip() for c in table.rows[0].cells] if table.rows else []
            for r_idx, row in enumerate(table.rows[1:], start=1):
                values = [c.text.strip() for c in row.cells]
                pairs = [f"{h}: {v}" for h, v in zip(header, values) if v]
                text = " | ".join(pairs) if pairs else " | ".join(v for v in values if v)
                if text:
                    elements.append(
                        Element(
                            type=ElementType.TABLE, text=text,
                            metadata={"table": t_idx, "row": r_idx},
                        )
                    )
        return ParsedDocument(
            source_name=source_name, parser=self.name, elements=elements
        )
