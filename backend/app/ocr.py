"""OCR for scanned documents and image uploads, using an OpenAI vision model.

We deliberately avoid Tesseract / system binaries so the app runs anywhere the
OpenAI dependency is available. Scanned PDF pages are rasterised with PyMuPDF
and, together with uploaded images, sent to a vision-capable model for
transcription. Nothing is written to disk.
"""
from __future__ import annotations

import base64
import io
import os
from typing import List, Tuple

from .llm import LLMConfigError, _client

# Vision model; defaults to the main model (gpt-4o-mini is vision-capable).
VISION_MODEL = os.getenv(
    "OPENAI_VISION_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")
)

# Bound cost/latency: at most this many page-images are OCR'd per document.
MAX_OCR_PAGES = int(os.getenv("MAX_OCR_PAGES", "10"))

# Resolution for rasterising PDF pages. 150 DPI is a good OCR accuracy/size
# trade-off for typical text documents.
OCR_DPI = int(os.getenv("OCR_DPI", "150"))

# Image extensions we accept as direct uploads.
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}

_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/png",   # normalised below
    ".tiff": "image/png",  # normalised below
}


def is_ocr_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def pdf_to_images(data: bytes, max_pages: int = MAX_OCR_PAGES) -> List[Tuple[str, bytes]]:
    """Rasterise up to ``max_pages`` PDF pages to PNG images (mime, bytes)."""
    import fitz  # PyMuPDF; imported lazily so text-only paths don't need it.

    images: List[Tuple[str, bytes]] = []
    zoom = OCR_DPI / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            if len(images) >= max_pages:
                break
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            images.append(("image/png", pix.tobytes("png")))
    return images


def image_upload_to_images(filename: str, data: bytes) -> List[Tuple[str, bytes]]:
    """Prepare a single uploaded image for OCR.

    TIFF/BMP are converted to PNG when Pillow is available, since some vision
    endpoints reject them; otherwise the raw bytes are passed through.
    """
    ext = os.path.splitext(filename or "")[1].lower()
    mime = _MIME_BY_EXT.get(ext, "image/png")
    if ext in {".tif", ".tiff", ".bmp"}:
        converted = _to_png(data)
        if converted is not None:
            return [("image/png", converted)]
    return [(mime, data)]


def _to_png(data: bytes) -> bytes | None:
    try:
        from PIL import Image  # optional
    except Exception:
        return None
    try:
        with Image.open(io.BytesIO(data)) as im:
            buf = io.BytesIO()
            im.convert("RGB").save(buf, format="PNG")
            return buf.getvalue()
    except Exception:
        return None


def ocr_images(images: List[Tuple[str, bytes]]) -> str:
    """Transcribe text from page images via the vision model."""
    if not images:
        return ""
    if not is_ocr_configured():
        raise LLMConfigError(
            "OPENAI_API_KEY is not set. It is required to read scanned or "
            "image-based documents (OCR)."
        )

    client = _client()

    content = [
        {
            "type": "text",
            "text": (
                "You are an OCR engine. Transcribe ALL text from the following "
                "document page image(s) exactly as it appears, preserving the "
                "natural reading order and line breaks. Keep tables readable "
                "using tabs or spaces. Do NOT add commentary, headings, or "
                "explanations. If a page contains no readable text, skip it."
            ),
        }
    ]
    for mime, raw in images:
        b64 = base64.b64encode(raw).decode("ascii")
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
        )

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[{"role": "user", "content": content}],
        temperature=0,
    )
    return (response.choices[0].message.content or "").strip()
