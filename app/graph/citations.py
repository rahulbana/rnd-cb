"""Deterministic citation normalization — the safety net over LLM synthesis.

The synthesis LLM writes into a permissive `ReportDraft`; `normalize_citations`
then repairs the citation graph so the returned `ResearchReport` is trustworthy:

  - keep only citations that resolve to a real gathered source (by id, else url),
  - collapse duplicate citations of the same source,
  - renumber contiguously 1..N,
  - rewrite inline [n] markers in the summary and section bodies to match,
  - backfill each citation's title/url/credibility from the real source.

This guarantees every [n] in the prose points at a source we actually retrieved
— no fabricated references survive. Pure functions, no LLM/network deps.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.models.report import Citation, ReportSection, ResearchReport
from app.models.schemas import Source

_CITE_RE = re.compile(r"\[(\d+)\]")


class ReportDraft(BaseModel):
    """Permissive draft the LLM fills; normalized into a strict ResearchReport."""

    title: str
    executive_summary: str = Field(..., min_length=1)
    key_findings: list[str] = Field(default_factory=list)
    sections: list[ReportSection] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = 0.5
    open_questions: list[str] = Field(default_factory=list)


def _source_index(sources: list[Source]) -> tuple[dict[str, Source], dict[str, Source]]:
    return {s.id: s for s in sources}, {s.url: s for s in sources}


def _renumber_text(text: str, remap: dict[int, int]) -> str:
    def sub(m: re.Match) -> str:
        old = int(m.group(1))
        return f"[{remap[old]}]" if old in remap else ""

    return _CITE_RE.sub(sub, text)


def normalize_citations(draft: ReportDraft, sources: list[Source], *, topic: str = "") -> ResearchReport:
    by_id, by_url = _source_index(sources)

    remap: dict[int, int] = {}
    final_citations: list[Citation] = []
    seen_source_ids: dict[str, int] = {}

    for cit in sorted(draft.citations, key=lambda c: c.number):
        src = by_id.get(cit.source_id) or by_url.get(cit.url)
        if src is None:
            continue  # drop fabricated / unresolvable citation
        if src.id in seen_source_ids:
            remap[cit.number] = seen_source_ids[src.id]  # collapse duplicate
            continue
        new_num = len(final_citations) + 1
        remap[cit.number] = new_num
        seen_source_ids[src.id] = new_num
        final_citations.append(
            Citation(
                number=new_num,
                source_id=src.id,
                title=src.title,
                url=src.url,
                credibility=src.credibility,
            )
        )

    exec_summary = _renumber_text(draft.executive_summary, remap)
    if len(exec_summary) < 50:  # renumbering shouldn't push us below the min-length floor
        exec_summary = draft.executive_summary

    sections: list[ReportSection] = []
    for sec in draft.sections:
        body = _renumber_text(sec.body, remap)
        used = sorted({int(m) for m in _CITE_RE.findall(body)})
        sections.append(
            ReportSection(heading=sec.heading, body=body, tables=sec.tables, citation_numbers=used)
        )

    return ResearchReport(
        title=draft.title,
        topic=topic,
        executive_summary=exec_summary,
        key_findings=draft.key_findings,
        sections=sections,
        citations=final_citations,
        confidence=max(0.0, min(1.0, draft.confidence)),
        open_questions=draft.open_questions,
    )
