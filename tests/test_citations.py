from app.graph.citations import ReportDraft, normalize_citations
from app.models.report import Citation, ReportSection
from app.models.schemas import Source


def _sources():
    return [
        Source(id="aaa", title="Alpha", url="https://a.com", credibility=0.9),
        Source(id="bbb", title="Beta", url="https://b.com", credibility=0.7),
    ]


def test_drops_fabricated_citation_and_renumbers():
    draft = ReportDraft(
        title="T",
        executive_summary="Alpha says X [1]. Ghost says Y [2]. " + "pad " * 10,
        sections=[ReportSection(heading="H", body="Body cites [1] and ghost [2].")],
        citations=[
            Citation(number=1, source_id="aaa", title="?", url="?"),
            Citation(number=2, source_id="ZZZ-not-real", title="?", url="?"),
        ],
    )
    report = normalize_citations(draft, _sources(), topic="topic")
    # only the resolvable citation survives, numbered 1
    assert len(report.citations) == 1
    assert report.citations[0].number == 1
    assert report.citations[0].source_id == "aaa"
    # fabricated [2] marker is stripped from prose
    assert "[2]" not in report.executive_summary
    assert "[2]" not in report.sections[0].body
    assert "[1]" in report.sections[0].body
    # backfilled from the real source
    assert report.citations[0].title == "Alpha"
    assert report.citations[0].url == "https://a.com"


def test_renumbers_to_contiguous_when_llm_skips_numbers():
    draft = ReportDraft(
        title="T",
        executive_summary="Claim from beta [5]. " + "pad " * 20,
        sections=[ReportSection(heading="H", body="See [5] and [9].")],
        citations=[
            Citation(number=5, source_id="bbb", title="?", url="?"),
            Citation(number=9, source_id="aaa", title="?", url="?"),
        ],
    )
    report = normalize_citations(draft, _sources(), topic="t")
    nums = sorted(c.number for c in report.citations)
    assert nums == [1, 2]  # contiguous, passes ResearchReport validator
    # [5] -> [1], [9] -> [2]
    assert "[1]" in report.sections[0].body
    assert "[2]" in report.sections[0].body


def test_collapses_duplicate_citations_of_same_source():
    draft = ReportDraft(
        title="T",
        executive_summary="A [1] and again A [2]. " + "pad " * 20,
        sections=[ReportSection(heading="H", body="[1] then [2].")],
        citations=[
            Citation(number=1, source_id="aaa", title="?", url="?"),
            Citation(number=2, source_id="aaa", title="?", url="?"),
        ],
    )
    report = normalize_citations(draft, _sources(), topic="t")
    assert len(report.citations) == 1
    # both markers collapse to [1]
    assert report.sections[0].body.count("[1]") == 2


def test_resolves_by_url_when_id_missing():
    draft = ReportDraft(
        title="T",
        executive_summary="Cited by url [1]. " + "pad " * 20,
        sections=[ReportSection(heading="H", body="body [1]")],
        citations=[Citation(number=1, source_id="", title="?", url="https://b.com")],
    )
    report = normalize_citations(draft, _sources(), topic="t")
    assert len(report.citations) == 1
    assert report.citations[0].source_id == "bbb"
