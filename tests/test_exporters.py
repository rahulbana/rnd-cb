import zipfile

from code_reviewer.exporters import render_markdown, write_docx, write_markdown
from code_reviewer.models import (
    CategoryResult,
    FileReview,
    Finding,
    ReviewReport,
    Severity,
)


def _sample_report() -> ReviewReport:
    finding = Finding(
        title="Hardcoded secret",
        description="API key in source.",
        severity=Severity.CRITICAL,
        line=1,
        recommendation="Move to env var.",
    )
    result = CategoryResult(
        category="Security",
        file_path="app.py",
        findings=[finding],
        summary="Found a secret.",
    )
    clean = CategoryResult(category="Correctness", file_path="app.py")
    return ReviewReport(
        root="/proj",
        language="python",
        model="gpt-4o-mini",
        files=[FileReview(file_path="app.py", results=[result, clean])],
    )


def test_render_markdown_contains_finding():
    md = render_markdown(_sample_report())
    assert "# AI Code Review" in md
    assert "Hardcoded secret" in md
    assert "CRITICAL" in md
    assert "Move to env var." in md


def test_write_markdown(tmp_path):
    out = tmp_path / "report.md"
    write_markdown(_sample_report(), str(out))
    assert out.exists()
    assert "Hardcoded secret" in out.read_text(encoding="utf-8")


def test_write_docx(tmp_path):
    out = tmp_path / "report.docx"
    write_docx(_sample_report(), str(out))
    assert out.exists()
    # A valid .docx is a zip archive containing the main document part.
    with zipfile.ZipFile(out) as zf:
        assert "word/document.xml" in zf.namelist()
        body = zf.read("word/document.xml").decode("utf-8")
    assert "Hardcoded secret" in body
