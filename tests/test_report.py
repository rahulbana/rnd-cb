import pytest
from pydantic import ValidationError

from app.models.report import Citation, ReportSection, ReportTable, ResearchReport


def _report(**over):
    base = dict(
        title="T",
        topic="topic",
        executive_summary="x" * 60,
        sections=[ReportSection(heading="H", body="body [1]")],
        citations=[Citation(number=1, source_id="s1", title="Src", url="https://a.com")],
    )
    base.update(over)
    return ResearchReport(**base)


def test_valid_report_roundtrips_markdown():
    r = _report()
    md = r.to_markdown()
    assert "## Executive Summary" in md
    assert "## References" in md
    assert "[Src](https://a.com)" in md


def test_citations_must_be_contiguous():
    with pytest.raises(ValidationError):
        _report(citations=[Citation(number=2, source_id="s", title="t", url="u")])


def test_table_shape_validation():
    with pytest.raises(ValidationError):
        ReportTable(title="t", columns=["a", "b"], rows=[["1"]])


def test_table_to_markdown():
    t = ReportTable(title="Cmp", columns=["Name", "Val"], rows=[["A", "1"], ["B", "2"]])
    md = t.to_markdown()
    assert "| Name | Val |" in md
    assert "| A | 1 |" in md


def test_exec_summary_min_length():
    with pytest.raises(ValidationError):
        _report(executive_summary="too short")
