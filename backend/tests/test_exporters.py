"""Tests for the Markdown and PDF exporters."""
from __future__ import annotations

from pypdf import PdfReader

from app.services.exporters import build_pdf, plan_filename, render_markdown


def test_markdown_contains_sections(sample_plan):
    md = render_markdown(sample_plan)
    for heading in ["# ", "## 📚 Curriculum", "## 🗓️ Schedule", "## 📝 Quiz"]:
        assert heading in md
    assert "parabola" in md
    assert "### Case-Based Questions" in md


def test_pdf_is_valid_and_has_no_literal_tags(sample_plan, tmp_path):
    pdf = build_pdf(sample_plan)
    assert pdf[:5] == b"%PDF-"

    path = tmp_path / "plan.pdf"
    path.write_bytes(pdf)
    text = "\n".join(p.extract_text() for p in PdfReader(str(path)).pages)

    for tag in ["<br/>", "<font", "</font>", "<b>", "</b>", "<link", "&lt;", "&amp;"]:
        assert tag not in text, f"literal markup {tag!r} leaked into the PDF"
    assert "Answer:" in text


def test_plan_filename(sample_plan):
    name = plan_filename(sample_plan, "pdf")
    assert name.endswith(".pdf")
    assert "--" not in name
    assert name == "study-plan-math-quadratics.pdf"
