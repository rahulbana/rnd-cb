"""PDF parser with switchable extraction backends.

Backends (selected via ``RAG_PDF_BACKEND``):
  * ``pymupdf``      - fast text extraction (PyMuPDF/fitz), default.
  * ``pdfplumber``   - superior table extraction.
  * ``unstructured`` - layout-aware partitioning into typed elements.
  * ``docling``      - ML document conversion to structured markdown.

When ``pdf_ocr_fallback`` is on, any page yielding no extractable text is
rendered to an image and run through Tesseract, so scanned PDFs still work.
"""
from __future__ import annotations

from ..models import Element, ElementType, ParsedDocument
from .base import BaseParser, ParserError, require
from ...config import get_settings
from ...core.logging import get_logger

log = get_logger(__name__)


class PDFParser(BaseParser):
    name = "pdf"

    def __init__(self, backend: str | None = None) -> None:
        self.backend = backend or get_settings().pdf_backend

    def parse(self, path: str, source_name: str) -> ParsedDocument:
        dispatch = {
            "pymupdf": self._parse_pymupdf,
            "pdfplumber": self._parse_pdfplumber,
            "unstructured": self._parse_unstructured,
            "docling": self._parse_docling,
        }
        fn = dispatch.get(self.backend)
        if fn is None:
            raise ParserError(f"Unknown PDF backend: {self.backend}")
        doc = fn(path, source_name)
        doc.metadata["backend"] = self.backend
        return doc

    # --- PyMuPDF (default) + OCR fallback ------------------------------------
    def _parse_pymupdf(self, path: str, source_name: str) -> ParsedDocument:
        fitz = require("fitz", "pymupdf")
        settings = get_settings()
        elements: list[Element] = []
        with fitz.open(path) as pdf:
            for page_no, page in enumerate(pdf, start=1):
                text = page.get_text("text").strip()
                if text:
                    for block in text.split("\n\n"):
                        block = block.strip()
                        if block:
                            elements.append(
                                Element(type=ElementType.TEXT, text=block,
                                        metadata={"page": page_no})
                            )
                elif settings.pdf_ocr_fallback:
                    ocr_text = self._ocr_page(fitz, page, settings.ocr_language)
                    if ocr_text:
                        elements.append(
                            Element(type=ElementType.OCR, text=ocr_text,
                                    metadata={"page": page_no, "ocr": True})
                        )
        return ParsedDocument(source_name=source_name, parser="pdf:pymupdf",
                              elements=elements)

    @staticmethod
    def _ocr_page(fitz, page, language: str) -> str:
        try:
            pytesseract = require("pytesseract", "pytesseract")
            pil = require("PIL.Image", "Pillow")
            import io
            pix = page.get_pixmap(dpi=200)
            image = pil.open(io.BytesIO(pix.tobytes("png")))
            return pytesseract.image_to_string(image, lang=language).strip()
        except ParserError as exc:
            log.warning("OCR fallback unavailable: %s", exc)
            return ""

    # --- pdfplumber (best tables) --------------------------------------------
    def _parse_pdfplumber(self, path: str, source_name: str) -> ParsedDocument:
        pdfplumber = require("pdfplumber", "pdfplumber")
        elements: list[Element] = []
        with pdfplumber.open(path) as pdf:
            for page_no, page in enumerate(pdf.pages, start=1):
                for table in page.extract_tables() or []:
                    if not table:
                        continue
                    header = [str(c or "") for c in table[0]]
                    for row in table[1:]:
                        pairs = [f"{h}: {v}" for h, v in zip(header, row) if v]
                        text = " | ".join(pairs)
                        if text:
                            elements.append(
                                Element(type=ElementType.TABLE, text=text,
                                        metadata={"page": page_no})
                            )
                text = (page.extract_text() or "").strip()
                if text:
                    elements.append(
                        Element(type=ElementType.TEXT, text=text,
                                metadata={"page": page_no})
                    )
        return ParsedDocument(source_name=source_name, parser="pdf:pdfplumber",
                              elements=elements)

    # --- Unstructured (layout-aware) -----------------------------------------
    def _parse_unstructured(self, path: str, source_name: str) -> ParsedDocument:
        mod = require("unstructured.partition.pdf", "'unstructured[pdf]'")
        raw = mod.partition_pdf(filename=path, strategy="hi_res")
        elements = _from_unstructured(raw)
        return ParsedDocument(source_name=source_name, parser="pdf:unstructured",
                              elements=elements)

    # --- Docling (ML conversion) ---------------------------------------------
    def _parse_docling(self, path: str, source_name: str) -> ParsedDocument:
        dc = require("docling.document_converter", "docling")
        converter = dc.DocumentConverter()
        result = converter.convert(path)
        markdown = result.document.export_to_markdown()
        elements: list[Element] = []
        for block in markdown.split("\n\n"):
            block = block.strip()
            if not block:
                continue
            etype = ElementType.TITLE if block.startswith("#") else ElementType.TEXT
            elements.append(Element(type=etype, text=block))
        return ParsedDocument(source_name=source_name, parser="pdf:docling",
                              elements=elements)


def _from_unstructured(raw_elements) -> list[Element]:
    """Map unstructured's element categories onto our normalized types."""
    mapping = {
        "Title": ElementType.TITLE,
        "NarrativeText": ElementType.TEXT,
        "ListItem": ElementType.LIST,
        "Table": ElementType.TABLE,
        "FigureCaption": ElementType.CAPTION,
    }
    out: list[Element] = []
    for el in raw_elements:
        text = (getattr(el, "text", "") or "").strip()
        if not text:
            continue
        category = el.__class__.__name__
        meta = {}
        page = getattr(getattr(el, "metadata", None), "page_number", None)
        if page is not None:
            meta["page"] = page
        out.append(Element(type=mapping.get(category, ElementType.TEXT),
                           text=text, metadata=meta))
    return out
