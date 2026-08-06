"""Extract plain text from a variety of file types (for summarizing uploads)."""
from __future__ import annotations

from pathlib import Path

PLAIN_SUFFIXES = {
    ".txt", ".md", ".markdown", ".csv", ".json", ".xml", ".log",
    ".py", ".js", ".html", ".htm", ".rst", ".yaml", ".yml", ".ini",
}


class UnsupportedFile(Exception):
    """The file type cannot be read as text."""


def read_text_from_file(path: str, max_chars: int = 200_000) -> str:
    """Return the textual content of a file. Raises UnsupportedFile on binary types."""
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(str(p))

    suffix = p.suffix.lower()

    if suffix in PLAIN_SUFFIXES:
        text = p.read_text(encoding="utf-8", errors="replace")
    elif suffix == ".docx":
        text = _read_docx(p)
    elif suffix == ".pdf":
        text = _read_pdf(p)
    else:
        # Best-effort: try to decode as UTF-8 text; reject if it looks binary.
        try:
            raw = p.read_bytes()
            if b"\x00" in raw[:4096]:
                raise UnsupportedFile(f"'{suffix or 'file'}' is not a readable text type.")
            text = raw.decode("utf-8", errors="replace")
        except UnsupportedFile:
            raise
        except Exception as exc:  # noqa: BLE001
            raise UnsupportedFile(f"Could not read '{p.name}': {exc}") from exc

    return text[:max_chars]


def _read_docx(p: Path) -> str:
    from docx import Document

    doc = Document(str(p))
    return "\n".join(para.text for para in doc.paragraphs if para.text)


def _read_pdf(p: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(p))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001
            continue
    return "\n".join(parts)
