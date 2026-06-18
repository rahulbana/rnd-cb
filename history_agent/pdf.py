"""Render a Markdown report to a sectioned PDF.

Each top-level section (a ``##`` heading) starts on its own page, so the output
reads "section by section, one section per page". Inline Markdown — bold,
italics, ``code`` and ``[links](url)`` — is converted to styled text, bullet and
numbered lists are rendered as lists, and every page is numbered.

The heavy lifting uses ReportLab, which is pure-Python (no system libraries).
"""

from __future__ import annotations

import html
import re
from datetime import datetime

# A standalone heading line, e.g. "## Sports".
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
# A bullet list item: "- ", "* " or "+ ".
_BULLET_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
# A numbered list item: "1. ", "2) " etc.
_NUMBER_RE = re.compile(r"^\s*\d+[.)]\s+(.*)$")
# A horizontal rule: "---", "***", "___".
_HRULE_RE = re.compile(r"^\s*([-*_])\1{2,}\s*$")


def _inline(text: str) -> str:
    """Convert inline Markdown to the mini-markup ReportLab's Paragraph accepts."""
    text = html.escape(text, quote=False)
    # Links: [label](url) -> underlined blue anchor.
    text = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        r'<a href="\2" color="#1a56db"><u>\1</u></a>',
        text,
    )
    # Bold then italics (order matters so ** isn't eaten by the * rule).
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", r'<font face="Courier">\1</font>', text)
    return text


def _build_styles():
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    base = getSampleStyleSheet()
    styles = {
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontSize=22, leading=26,
            spaceAfter=14, textColor="#0b3d91",
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontSize=16, leading=20,
            spaceBefore=4, spaceAfter=10, textColor="#0b3d91",
        ),
        "h3": ParagraphStyle(
            "H3", parent=base["Heading3"], fontSize=13, leading=17,
            spaceBefore=8, spaceAfter=6, textColor="#333333",
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontSize=10.5, leading=15,
            spaceAfter=6, alignment=TA_LEFT,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["BodyText"], fontSize=10.5, leading=15,
        ),
    }
    return styles


def _markdown_to_flowables(markdown: str, styles):
    """Parse Markdown into ReportLab flowables with a page break per ``##`` section."""
    from reportlab.platypus import ListFlowable, ListItem, PageBreak, Paragraph, Spacer

    flowables: list = []
    para_lines: list[str] = []
    list_items: list[tuple[str, str]] = []  # (kind, text); kind is "ul" or "ol"
    seen_section = False

    def flush_para():
        if para_lines:
            text = " ".join(line.strip() for line in para_lines).strip()
            if text:
                flowables.append(Paragraph(_inline(text), styles["body"]))
            para_lines.clear()

    def flush_list():
        if list_items:
            kind = list_items[0][0]
            items = [
                ListItem(Paragraph(_inline(t), styles["bullet"]))
                for _, t in list_items
            ]
            flowables.append(
                ListFlowable(
                    items,
                    bulletType="bullet" if kind == "ul" else "1",
                    bulletFontSize=10.5,
                    leftIndent=18,
                    spaceAfter=8,
                )
            )
            list_items.clear()

    for raw in markdown.splitlines():
        line = raw.rstrip()

        heading = _HEADING_RE.match(line)
        if heading:
            flush_para()
            flush_list()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            # Each ## section after the first starts on a new page. The ``#``
            # title is kept with the first section rather than on a lonely page.
            if level == 2:
                if seen_section:
                    flowables.append(PageBreak())
                seen_section = True
            style = styles["h1"] if level == 1 else styles["h2"] if level == 2 else styles["h3"]
            flowables.append(Paragraph(_inline(text), style))
            continue

        if _HRULE_RE.match(line):
            flush_para()
            flush_list()
            flowables.append(Spacer(1, 6))
            continue

        bullet = _BULLET_RE.match(line)
        if bullet:
            flush_para()
            list_items.append(("ul", bullet.group(1).strip()))
            continue

        number = _NUMBER_RE.match(line)
        if number:
            flush_para()
            list_items.append(("ol", number.group(1).strip()))
            continue

        if not line.strip():
            flush_para()
            flush_list()
            continue

        # Plain text: a list ends when a non-list line appears.
        flush_list()
        para_lines.append(line)

    flush_para()
    flush_list()
    return flowables


def _make_page_decorator(footer_label: str):
    """Return an onPage callback that draws a footer with the page number."""

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor("#888888")
        width = doc.pagesize[0]
        canvas.drawString(2 * 28.35, 1.2 * 28.35, footer_label)
        canvas.drawRightString(
            width - 2 * 28.35, 1.2 * 28.35, f"Page {doc.page}"
        )
        canvas.restoreState()

    return decorate


def render_markdown_to_pdf(markdown: str, output_path: str, *, title: str | None = None) -> str:
    """Render a Markdown report to a sectioned PDF file.

    Args:
        markdown: The report body in Markdown.
        output_path: Where to write the ``.pdf``.
        title: Optional document title (used for PDF metadata and the footer).

    Returns:
        The output path.

    Raises:
        RuntimeError: If ReportLab is not installed.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate
    except ImportError as exc:  # pragma: no cover - exercised only without the dep
        raise RuntimeError(
            "The 'reportlab' package is required for PDF output. "
            "Run: pip install -r requirements.txt"
        ) from exc

    import os

    parent = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(parent, exist_ok=True)

    margin = 2 * 28.35  # 2 cm in points
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title=title or "On This Day",
        author="on-this-day agent",
    )
    styles = _build_styles()
    flowables = _markdown_to_flowables(markdown, styles)

    footer = title or "On This Day"
    footer = f"{footer}  ·  generated {datetime.now():%Y-%m-%d}"
    decorate = _make_page_decorator(footer)
    doc.build(flowables, onFirstPage=decorate, onLaterPages=decorate)
    return output_path
