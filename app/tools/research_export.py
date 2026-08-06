"""Save research/results to a file (Markdown, Word .docx, or PDF)."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from ..config import config
from .base import Tool, err, ok


def _safe_name(title: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")
    slug = slug[:60] or "research"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{slug}_{stamp}"


def _save_md(title: str, content: str, path: Path) -> None:
    path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")


def _save_docx(title: str, content: str, path: Path) -> None:
    from docx import Document

    doc = Document()
    doc.add_heading(title, level=0)
    for block in content.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("# "):
            doc.add_heading(block[2:], level=1)
        elif block.startswith("## "):
            doc.add_heading(block[3:], level=2)
        else:
            doc.add_paragraph(block)
    doc.save(path)


def _save_pdf(title: str, content: str, path: Path) -> None:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    def latin1(s: str) -> str:
        # Core PDF fonts are latin-1 only; replace anything outside it.
        return s.encode("latin-1", "replace").decode("latin-1")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    # Keep the cursor at the left margin after every block so full-width
    # multi_cell calls always have the full page width to work with.
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, latin1(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_font("Helvetica", size=12)
    for line in content.split("\n"):
        text = latin1(line)
        if not text.strip():
            pdf.ln(4)
            continue
        pdf.multi_cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.output(str(path))


_WRITERS = {"md": _save_md, "markdown": _save_md, "docx": _save_docx,
            "doc": _save_docx, "pdf": _save_pdf}
_EXT = {"md": ".md", "markdown": ".md", "docx": ".docx", "doc": ".docx", "pdf": ".pdf"}


def save_research(title: str, content: str, format: str = "md") -> dict:
    """Save research content to a file in Markdown, Word, or PDF format."""
    fmt = format.lower().strip()
    if fmt not in _WRITERS:
        return err("Unsupported format. Use one of: md, docx, pdf.")

    filename = _safe_name(title) + _EXT[fmt]
    out = config.EXPORT_DIR / filename
    try:
        _WRITERS[fmt](title, content, out)
    except Exception as exc:
        return err(f"Failed to save {fmt} file: {exc}")

    return ok({
        "title": title,
        "format": fmt,
        "path": str(out),
        "bytes": out.stat().st_size,
    }, message=f"Saved research to {out}")


def get_tools() -> list[Tool]:
    return [
        Tool(
            name="save_research",
            description="Save research or results to a file on disk as Markdown "
                        "(md), Word (docx) or PDF. Returns the saved file path.",
            category="Research",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title."},
                    "content": {"type": "string", "description": "The body content to save."},
                    "format": {
                        "type": "string",
                        "enum": ["md", "docx", "pdf"],
                        "description": "Output format. Default 'md'.",
                    },
                },
                "required": ["title", "content"],
            },
            func=save_research,
        )
    ]
