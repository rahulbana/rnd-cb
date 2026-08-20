"""Extract plain text from uploaded documents.

Supported formats: PDF (including scanned/image PDFs via OCR), DOC/DOCX,
PPT/PPTX, TXT and other plain-text files (md, csv, rtf-as-text, etc.), and
image files (PNG/JPG/…) via OCR. Everything runs in-memory; nothing is written
to disk, in keeping with the "no persistent data" requirement.

Scanned documents: PDFs whose pages are images (no embedded text layer) and
uploaded image files are read with an OpenAI vision model — see ``ocr.py``.
"""
from __future__ import annotations

import io
import os
from dataclasses import dataclass

from pypdf import PdfReader
from docx import Document as DocxDocument
from pptx import Presentation

from . import ocr


class UnsupportedFileError(Exception):
    """Raised when a file cannot be parsed into text."""


@dataclass
class ParsedDocument:
    """Result of parsing an upload."""

    text: str
    ocr_used: bool = False


# Extensions we know how to read directly.
_PDF_EXTS = {".pdf"}
_DOCX_EXTS = {".docx"}
_PPTX_EXTS = {".pptx"}
_TEXT_EXTS = {".txt", ".text", ".md", ".markdown", ".csv", ".tsv", ".log", ".rtf"}
# Legacy binary Office formats that the pure-python libraries cannot read.
_LEGACY_EXTS = {".doc", ".ppt"}


def parse_document(filename: str, data: bytes, allow_ocr: bool = True) -> ParsedDocument:
    """Extract text from an upload, falling back to OCR for scanned inputs.

    ``allow_ocr=False`` disables the OpenAI vision path (used by offline tests).
    """
    ext = os.path.splitext(filename or "")[1].lower()
    ocr_used = False

    if ext in ocr.IMAGE_EXTS:
        # Image uploads are always OCR'd.
        if not allow_ocr:
            raise UnsupportedFileError("Image OCR is disabled.")
        images = ocr.image_upload_to_images(filename, data)
        text = ocr.ocr_images(images)
        ocr_used = True
    elif ext in _PDF_EXTS:
        text = _from_pdf(data)
        if allow_ocr and _looks_scanned(text, _pdf_page_count(data)):
            # No usable text layer → treat as scanned and OCR the pages.
            ocr_text = _ocr_pdf(data)
            if ocr_text.strip():
                text = ocr_text
                ocr_used = True
    elif ext in _DOCX_EXTS:
        text = _from_docx(data)
    elif ext in _PPTX_EXTS:
        text = _from_pptx(data)
    elif ext in _TEXT_EXTS:
        text = _from_text(data)
    elif ext in _LEGACY_EXTS:
        # Best-effort: some .doc/.ppt files are actually the modern format or
        # plain text with a misleading extension. Try, then guide the user.
        text = _best_effort(data)
        if not text.strip():
            raise UnsupportedFileError(
                f"Legacy '{ext}' files are not supported directly. Please "
                f"re-save the file as {'.docx' if ext == '.doc' else '.pptx'} "
                "or PDF and upload again."
            )
    else:
        # Unknown extension — try to sniff it before giving up.
        text = _best_effort(data)
        if not text.strip() and allow_ocr and _is_probably_image(data):
            text = ocr.ocr_images([("image/png", data)])
            ocr_used = True
        if not text.strip():
            raise UnsupportedFileError(
                f"Unsupported file type '{ext or 'unknown'}'. Supported types: "
                "PDF, DOCX, PPTX, images (scanned), and plain-text files."
            )

    text = _clean(text)
    if not text.strip():
        raise UnsupportedFileError(
            "No readable text could be extracted from this document. If it is a "
            "scanned file, ensure the pages are legible and try again."
        )
    return ParsedDocument(text=text, ocr_used=ocr_used)


def extract_text(filename: str, data: bytes, allow_ocr: bool = True) -> str:
    """Backward-compatible helper returning just the extracted text."""
    return parse_document(filename, data, allow_ocr=allow_ocr).text


def _pdf_page_count(data: bytes) -> int:
    try:
        return len(PdfReader(io.BytesIO(data)).pages)
    except Exception:
        return 1


def _looks_scanned(text: str, page_count: int) -> bool:
    """Heuristic: a scanned PDF yields little or no extractable text."""
    meaningful = len("".join(text.split()))
    if meaningful == 0:
        return True
    # Fewer than ~10 non-whitespace characters per page ⇒ effectively imageless.
    return meaningful < max(20, page_count * 10)


def _ocr_pdf(data: bytes) -> str:
    images = ocr.pdf_to_images(data)
    return ocr.ocr_images(images)


def _is_probably_image(data: bytes) -> bool:
    sigs = (b"\x89PNG", b"\xff\xd8\xff", b"GIF8", b"BM", b"II*\x00", b"MM\x00*", b"RIFF")
    return any(data[:8].startswith(s) for s in sigs)


def _from_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            # Skip pages that fail to parse rather than aborting the whole file.
            continue
    return "\n".join(parts)


def _from_docx(data: bytes) -> str:
    doc = DocxDocument(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs]
    # Include text held inside tables, which python-docx keeps separate.
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text for cell in row.cells]
            parts.append("\t".join(cells))
    return "\n".join(parts)


def _from_pptx(data: bytes) -> str:
    prs = Presentation(io.BytesIO(data))
    parts = []
    for idx, slide in enumerate(prs.slides, start=1):
        parts.append(f"[Slide {idx}]")
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    line = "".join(run.text for run in para.runs)
                    if line:
                        parts.append(line)
            if shape.has_table:
                for row in shape.table.rows:
                    cells = [cell.text for cell in row.cells]
                    parts.append("\t".join(cells))
    return "\n".join(parts)


def _from_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def _best_effort(data: bytes) -> str:
    """Try each known parser; return the first that yields text."""
    for parser in (_from_pdf, _from_docx, _from_pptx):
        try:
            text = parser(data)
            if text.strip():
                return text
        except Exception:
            continue
    return _from_text(data)


def _clean(text: str) -> str:
    """Collapse excessive whitespace while preserving paragraph breaks."""
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned = []
    blank_run = 0
    for line in lines:
        if line.strip():
            cleaned.append(line)
            blank_run = 0
        else:
            blank_run += 1
            if blank_run <= 1:
                cleaned.append("")
    return "\n".join(cleaned).strip()
