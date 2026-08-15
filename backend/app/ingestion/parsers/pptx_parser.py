"""PowerPoint (.pptx) parser using python-pptx.

Each slide's shapes are walked for text frames and tables. Speaker notes are
included as captions. Elements carry the slide index for provenance.
"""
from __future__ import annotations

from ..models import Element, ElementType, ParsedDocument
from .base import BaseParser, require


class PptxParser(BaseParser):
    name = "pptx"

    def parse(self, path: str, source_name: str) -> ParsedDocument:
        pptx = require("pptx", "python-pptx")
        presentation = pptx.Presentation(path)
        elements: list[Element] = []

        for s_idx, slide in enumerate(presentation.slides, start=1):
            for shape in slide.shapes:
                if shape.has_table:
                    table = shape.table
                    header = [c.text.strip() for c in table.rows[0].cells] \
                        if table.rows else []
                    for row in list(table.rows)[1:]:
                        values = [c.text.strip() for c in row.cells]
                        pairs = [f"{h}: {v}" for h, v in zip(header, values) if v]
                        text = " | ".join(pairs) if pairs else " | ".join(values)
                        if text.strip():
                            elements.append(
                                Element(type=ElementType.TABLE, text=text,
                                        metadata={"slide": s_idx})
                            )
                    continue
                if not shape.has_text_frame:
                    continue
                for para in shape.text_frame.paragraphs:
                    text = "".join(run.text for run in para.runs).strip()
                    if not text:
                        continue
                    # The title placeholder (if any) becomes a TITLE element.
                    is_title = getattr(shape, "is_placeholder", False) and \
                        getattr(shape.placeholder_format, "idx", None) == 0
                    elements.append(
                        Element(
                            type=ElementType.TITLE if is_title else ElementType.TEXT,
                            text=text, metadata={"slide": s_idx},
                        )
                    )

            notes = slide.notes_slide.notes_text_frame.text.strip() \
                if slide.has_notes_slide else ""
            if notes:
                elements.append(
                    Element(type=ElementType.CAPTION, text=f"Speaker notes: {notes}",
                            metadata={"slide": s_idx})
                )
        return ParsedDocument(
            source_name=source_name, parser=self.name, elements=elements
        )
