"""Render a `ResearchReport` to a PDF using ReportLab's Platypus."""

from __future__ import annotations

from pathlib import Path

from app.models.report import ResearchReport


def export_pdf(report: ResearchReport, path: str | Path) -> Path:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        ListFlowable,
        ListItem,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    styles = getSampleStyleSheet()
    path = Path(path)
    doc = SimpleDocTemplate(str(path), pagesize=LETTER, title=report.title)
    flow: list = []

    flow.append(Paragraph(report.title, styles["Title"]))
    flow.append(Paragraph(f"Topic: {report.topic} · Confidence: {report.confidence:.0%}", styles["Italic"]))
    flow.append(Spacer(1, 12))

    flow.append(Paragraph("Executive Summary", styles["Heading1"]))
    flow.append(Paragraph(report.executive_summary, styles["BodyText"]))

    if report.key_findings:
        flow.append(Paragraph("Key Findings", styles["Heading1"]))
        flow.append(
            ListFlowable(
                [ListItem(Paragraph(kf, styles["BodyText"])) for kf in report.key_findings],
                bulletType="bullet",
            )
        )

    for sec in report.sections:
        flow.append(Paragraph(sec.heading, styles["Heading1"]))
        flow.append(Paragraph(sec.body.replace("\n", "<br/>"), styles["BodyText"]))
        for tbl in sec.tables:
            flow.append(Paragraph(tbl.title, styles["Heading2"]))
            data = [tbl.columns] + tbl.rows
            t = Table(data, hAlign="LEFT")
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            flow.append(t)
            flow.append(Spacer(1, 8))

    if report.open_questions:
        flow.append(Paragraph("Open Questions &amp; Gaps", styles["Heading1"]))
        flow.append(
            ListFlowable(
                [ListItem(Paragraph(q, styles["BodyText"])) for q in report.open_questions],
                bulletType="bullet",
            )
        )

    if report.citations:
        flow.append(Paragraph("References", styles["Heading1"]))
        for c in sorted(report.citations, key=lambda x: x.number):
            flow.append(Paragraph(f"{c.number}. {c.title} — {c.url}", styles["BodyText"]))

    doc.build(flow)
    return path
