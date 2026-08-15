"""Image (PNG/JPEG) parser using pytesseract OCR.

Requires the Tesseract binary to be installed on the host (``apt-get install
tesseract-ocr`` / ``brew install tesseract``).
"""
from __future__ import annotations

from ..models import Element, ElementType, ParsedDocument
from .base import BaseParser, require
from ...config import get_settings


class ImageParser(BaseParser):
    name = "image"

    def parse(self, path: str, source_name: str) -> ParsedDocument:
        pytesseract = require("pytesseract", "pytesseract")
        pil = require("PIL.Image", "Pillow")
        settings = get_settings()
        image = pil.open(path)
        text = pytesseract.image_to_string(image, lang=settings.ocr_language).strip()
        elements: list[Element] = []
        if text:
            elements.append(
                Element(type=ElementType.OCR, text=text,
                        metadata={"width": image.width, "height": image.height})
            )
        else:
            elements.append(
                Element(type=ElementType.CAPTION,
                        text=f"[Image '{source_name}' contained no extractable text]")
            )
        return ParsedDocument(
            source_name=source_name, parser=self.name, elements=elements,
            mime_type="image", metadata={"ocr_language": settings.ocr_language},
        )
