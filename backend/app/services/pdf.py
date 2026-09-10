"""PDF text extraction utilities."""
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class PDFExtractionError(Exception):
    """Raised when text cannot be extracted from an uploaded PDF."""


def extract_text(data: bytes) -> str:
    """Extract and normalize text from a PDF byte stream.

    Raises PDFExtractionError if the file is not a readable PDF or if no
    text content can be recovered (e.g. a scanned image-only PDF).
    """
    try:
        reader = PdfReader(BytesIO(data))
    except (PdfReadError, Exception) as exc:  # pypdf raises a variety of errors
        raise PDFExtractionError(f"Could not read PDF: {exc}") from exc

    if reader.is_encrypted:
        # Try an empty password before giving up.
        try:
            reader.decrypt("")
        except Exception as exc:
            raise PDFExtractionError("PDF is password protected.") from exc

    parts: list[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            parts.append(text)

    combined = "\n\n".join(parts).strip()
    if not combined:
        raise PDFExtractionError(
            "No text could be extracted. The PDF may be a scanned image."
        )
    return combined
