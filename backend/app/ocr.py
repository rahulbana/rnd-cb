"""Local OCR for scanned documents and image uploads (Tesseract).

Text is extracted from scanned PDF pages and image files **locally** using
Tesseract via ``pytesseract``. The document itself (or its page images) is never
sent to OpenAI — only the resulting plain text is later passed to the LLM for
notes/question generation. Nothing is written to disk.

Requires the Tesseract binary to be installed on the host (e.g.
``apt-get install tesseract-ocr``). PDF pages are rasterised with PyMuPDF.
"""
from __future__ import annotations

import io
import os
from typing import List

# OCR language(s), e.g. "eng" or "eng+hin". Requires the matching Tesseract
# language packs to be installed.
OCR_LANG = os.getenv("OCR_LANG", "eng")

# Bound work: at most this many pages are OCR'd per document.
MAX_OCR_PAGES = int(os.getenv("MAX_OCR_PAGES", "20"))

# Rasterisation resolution for PDF pages. 300 DPI is the sweet spot for
# Tesseract accuracy on normal text.
OCR_DPI = int(os.getenv("OCR_DPI", "300"))

# Image extensions we accept as direct uploads.
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


class OCRError(Exception):
    """Raised when local OCR cannot run (e.g. Tesseract not installed)."""


def is_ocr_configured() -> bool:
    """True when the Tesseract binary is available."""
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def pdf_to_images(data: bytes, max_pages: int = MAX_OCR_PAGES) -> List[bytes]:
    """Rasterise up to ``max_pages`` PDF pages to PNG image bytes."""
    import fitz  # PyMuPDF; imported lazily so text-only paths don't need it.

    images: List[bytes] = []
    zoom = OCR_DPI / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            if len(images) >= max_pages:
                break
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            images.append(pix.tobytes("png"))
    return images


def image_upload_to_images(filename: str, data: bytes) -> List[bytes]:
    """Return the raw image bytes for a single uploaded image (as a 1-item list)."""
    return [data]


def ocr_images(images: List[bytes]) -> str:
    """Run Tesseract locally on each image and return the concatenated text."""
    if not images:
        return ""

    try:
        import pytesseract
        from PIL import Image, ImageOps
    except Exception as exc:  # pragma: no cover - import guard
        raise OCRError(
            "OCR dependencies are missing. Install 'pytesseract' and 'Pillow'."
        ) from exc

    if not is_ocr_configured():
        raise OCRError(
            "Tesseract OCR is not installed on the server. Install it (e.g. "
            "'apt-get install tesseract-ocr') to read scanned or image files."
        )

    pages: List[str] = []
    for raw in images:
        try:
            with Image.open(io.BytesIO(raw)) as im:
                # Grayscale + auto-contrast improves recognition on scans.
                prepared = ImageOps.autocontrast(im.convert("L"))
                text = pytesseract.image_to_string(prepared, lang=OCR_LANG)
        except Exception:
            # Skip an unreadable page rather than failing the whole document.
            continue
        if text.strip():
            pages.append(text.strip())

    return "\n\n".join(pages).strip()
