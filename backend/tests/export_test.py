"""Regression test: exports must include the FULL article body.

Guards against the bug where a heading and its following prose shared a
blank-line block and everything after the heading line was dropped from
PDF/DOCX output.
"""
import io

from app.services import export

BODY = """## Introduction
The world is changing fast. This intro paragraph explains the premise.

## Main Section
A key point with supporting detail that spans
multiple source lines.

Some **bold** and *italic* and a [link](https://example.com) inline.

### Subsection
- First bullet item
- Second bullet item
- Third bullet item

1. Numbered one
2. Numbered two

> A blockquote of wisdom.

## Conclusion
Final wrap-up paragraph that must not be dropped."""

PROBES = [
    "intro paragraph",
    "supporting detail",
    "bold",
    "italic",
    "First bullet",
    "Second bullet",
    "Third bullet",
    "Numbered one",
    "Numbered two",
    "blockquote of wisdom",
    "Final wrap-up",
]


class _Article:
    title = "Test"
    body = BODY
    summary = "sum"
    seo_description = ""
    keywords = []
    sentiment = "neutral"
    tags = []
    ner_tags = []
    sources = []
    banner_image = None


def main() -> None:
    art = _Article()

    md = export.to_markdown(art).decode()
    for p in PROBES:
        assert p in md, f"MARKDOWN missing: {p}"

    from docx import Document

    docx_text = "\n".join(
        p.text for p in Document(io.BytesIO(export.to_docx(art))).paragraphs
    )
    for p in PROBES:
        assert p in docx_text, f"DOCX missing: {p}"

    from pypdf import PdfReader

    pdf_text = "\n".join(
        pg.extract_text() for pg in PdfReader(io.BytesIO(export.to_pdf(art))).pages
    )
    for p in PROBES:
        assert p in pdf_text, f"PDF missing: {p}"

    print("EXPORT COMPLETENESS TEST PASSED ✅  (md, docx, pdf all include full body)")


if __name__ == "__main__":
    main()
