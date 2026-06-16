"""Render a BookReport to Markdown and PDF."""

from __future__ import annotations

import io

from .models import BookReport


def report_to_markdown(report: BookReport) -> str:
    b = report.book
    lines: list[str] = []
    lines.append(f"# {b.title}")
    lines.append("")
    lines.append(f"**Author:** {b.author}")
    if b.published_year:
        lines.append(f"**Published:** {b.published_year}")
    if b.genres:
        lines.append(f"**Genres:** {', '.join(b.genres)}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(b.summary or "_No summary available._")
    lines.append("")

    lines.append("## Reviews")
    lines.append("")
    if report.reviews:
        for r in report.reviews:
            rating = f" — {r.rating}/5" if r.rating is not None else ""
            header = f"### {r.reviewer_name} ({r.reviewer_type.value}){rating}"
            lines.append(header)
            lines.append(f"*Sentiment: {r.sentiment.value}*")
            if r.excerpt:
                lines.append("")
                lines.append(f"> {r.excerpt}")
            if r.source_url:
                lines.append("")
                lines.append(f"Source: [{r.source or r.source_url}]({r.source_url})")
            lines.append("")
    else:
        lines.append("_No reviews found._")
        lines.append("")

    v = report.verification
    lines.append("## Verification")
    lines.append("")
    lines.append(f"- **Verified:** {'yes' if v.verified else 'no'}")
    lines.append(f"- **Confidence:** {v.confidence:.0%}")
    if v.notes:
        lines.append(f"- **Notes:** {v.notes}")
    if v.flagged_claims:
        lines.append("- **Flagged claims:**")
        for c in v.flagged_claims:
            lines.append(f"  - {c}")
    lines.append("")

    if report.sources:
        lines.append("## Sources")
        lines.append("")
        for s in report.sources:
            lines.append(f"- {s}")
        lines.append("")

    lines.append("---")
    lines.append(f"_Generated {report.generated_at.isoformat()}_")
    return "\n".join(lines)


def report_to_pdf(report: BookReport) -> bytes:
    """Render the report to a simple, dependency-light PDF via reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        ListFlowable,
        ListItem,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title=report.book.title)
    styles = getSampleStyleSheet()
    story = []

    b = report.book
    story.append(Paragraph(_esc(b.title), styles["Title"]))
    meta = [f"Author: {b.author}"]
    if b.published_year:
        meta.append(f"Published: {b.published_year}")
    if b.genres:
        meta.append(f"Genres: {', '.join(b.genres)}")
    story.append(Paragraph(_esc(" | ".join(meta)), styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Summary", styles["Heading2"]))
    story.append(Paragraph(_esc(b.summary or "No summary available."), styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Reviews", styles["Heading2"]))
    if report.reviews:
        for r in report.reviews:
            rating = f" — {r.rating}/5" if r.rating is not None else ""
            story.append(
                Paragraph(
                    _esc(f"{r.reviewer_name} ({r.reviewer_type.value}){rating}"),
                    styles["Heading3"],
                )
            )
            story.append(
                Paragraph(_esc(f"Sentiment: {r.sentiment.value}"), styles["Italic"])
            )
            if r.excerpt:
                story.append(Paragraph(_esc(f"“{r.excerpt}”"), styles["Normal"]))
            if r.source_url:
                story.append(
                    Paragraph(_esc(f"Source: {r.source or r.source_url}"), styles["Normal"])
                )
            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("No reviews found.", styles["Normal"]))
    story.append(Spacer(1, 12))

    v = report.verification
    story.append(Paragraph("Verification", styles["Heading2"]))
    story.append(
        Paragraph(
            _esc(
                f"Verified: {'yes' if v.verified else 'no'} | "
                f"Confidence: {v.confidence:.0%}"
            ),
            styles["Normal"],
        )
    )
    if v.notes:
        story.append(Paragraph(_esc(v.notes), styles["Normal"]))
    if v.flagged_claims:
        story.append(
            ListFlowable(
                [ListItem(Paragraph(_esc(c), styles["Normal"])) for c in v.flagged_claims],
                bulletType="bullet",
            )
        )
    story.append(Spacer(1, 12))

    if report.sources:
        story.append(Paragraph("Sources", styles["Heading2"]))
        story.append(
            ListFlowable(
                [ListItem(Paragraph(_esc(s), styles["Normal"])) for s in report.sources],
                bulletType="bullet",
            )
        )

    doc.build(story)
    return buffer.getvalue()


def _esc(text: str) -> str:
    """Escape characters that confuse reportlab's mini-markup parser."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
