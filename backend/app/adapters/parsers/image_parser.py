"""OCR parser for scanned images (Tesseract via pytesseract + Pillow).

The OCR path for scanned images. In production Docling can also OCR (same
Tesseract engine under the hood); this direct adapter keeps the OCR path
local, lightweight, and testable. Both heavy pieces import lazily.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from app.domain.models import ParsedDocument, TextBlock

if TYPE_CHECKING:
    from app.core.config import Settings

_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
    "image/bmp",
    "image/webp",
}


class TesseractImageParser:
    """Runs OCR over an image and returns the recognized text."""

    name = "tesseract_image"

    @classmethod
    def from_settings(cls, settings: Settings) -> TesseractImageParser:
        return cls()

    def supports(self, mime_type: str) -> bool:
        return mime_type in _MIME_TYPES

    async def parse(
        self, data: bytes, *, filename: str, mime_type: str
    ) -> ParsedDocument:
        import pytesseract  # lazy import
        from PIL import Image  # lazy import

        image = Image.open(io.BytesIO(data))
        text = pytesseract.image_to_string(image)

        blocks = [
            TextBlock(text=line.strip(), page=1)
            for line in text.splitlines()
            if line.strip()
        ]

        return ParsedDocument(
            source_filename=filename,
            mime_type=mime_type,
            text_blocks=blocks,
            image_refs=[filename],
            page_count=1,
            parser_name=self.name,
        )
