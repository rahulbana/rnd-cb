"""LLM-as-judge factuality evaluation of a generated report.

Given the final report and the source evidence it was written from, an
independent judge model rates each major claim as SUPPORTED / PARTIAL /
UNSUPPORTED / CONTRADICTED against the provided sources, then aggregates into a
0-1 factuality score. This is a *grounding* check (are claims backed by the
retrieved evidence), not a world-truth oracle.

The result is returned to callers and, when Langfuse is configured, can be
attached to the trace as a score for offline eval dashboards.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.budget import BudgetTracker
from app.llm import LLM
from app.models.report import ResearchReport
from app.models.schemas import Source

Verdict = Literal["SUPPORTED", "PARTIAL", "UNSUPPORTED", "CONTRADICTED"]

_WEIGHTS: dict[str, float] = {
    "SUPPORTED": 1.0,
    "PARTIAL": 0.5,
    "UNSUPPORTED": 0.0,
    "CONTRADICTED": -0.5,  # actively penalized
}

JUDGE_SYSTEM = """You are a meticulous fact-checker. You are given a set of \
SOURCE excerpts and a list of CLAIMS extracted from a report written from those \
sources. For each claim, judge whether the SOURCES support it:

- SUPPORTED: directly backed by at least one source.
- PARTIAL: partly supported; some element is unverified.
- UNSUPPORTED: not found in the sources (may still be true, but ungrounded).
- CONTRADICTED: a source states the opposite.

Judge ONLY against the provided sources. Do not use outside knowledge."""

JUDGE_HUMAN = """SOURCES:
{sources}

CLAIMS:
{claims}

Return a verdict and one-line justification for each claim, plus overall notes."""


class ClaimVerdict(BaseModel):
    claim: str
    verdict: Verdict
    justification: str = ""


class JudgeOutput(BaseModel):
    verdicts: list[ClaimVerdict] = Field(default_factory=list)
    notes: str = ""


class FactualityReport(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0, description="Aggregate grounding score.")
    supported: int = 0
    partial: int = 0
    unsupported: int = 0
    contradicted: int = 0
    verdicts: list[ClaimVerdict] = Field(default_factory=list)
    notes: str = ""


def _extract_claims(report: ResearchReport, limit: int = 20) -> list[str]:
    """Pull checkable claims: key findings + first sentences of each section."""
    claims: list[str] = list(report.key_findings)
    for sec in report.sections:
        for sentence in sec.body.replace("\n", " ").split(". "):
            s = sentence.strip()
            if len(s) > 40 and any(ch.isdigit() for ch in s) or len(s) > 120:
                claims.append(s.rstrip(".") + ".")
                break
    # de-dup preserving order, cap length
    seen: set[str] = set()
    out: list[str] = []
    for c in claims:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out[:limit]


def _sources_block(sources: list[Source], limit: int = 30) -> str:
    top = sorted(sources, key=lambda s: s.credibility, reverse=True)[:limit]
    return "\n\n".join(
        f"[{s.id}] {s.title} ({s.url})\n{(s.content or s.snippet)[:800]}" for s in top
    ) or "(no sources)"


def _aggregate(verdicts: list[ClaimVerdict]) -> FactualityReport:
    counts = {"SUPPORTED": 0, "PARTIAL": 0, "UNSUPPORTED": 0, "CONTRADICTED": 0}
    for v in verdicts:
        counts[v.verdict] += 1
    n = len(verdicts)
    if n == 0:
        return FactualityReport(score=0.0)
    raw = sum(_WEIGHTS[v.verdict] for v in verdicts) / n
    score = max(0.0, min(1.0, raw))
    return FactualityReport(
        score=round(score, 4),
        supported=counts["SUPPORTED"],
        partial=counts["PARTIAL"],
        unsupported=counts["UNSUPPORTED"],
        contradicted=counts["CONTRADICTED"],
        verdicts=verdicts,
    )


async def judge_report(
    report: ResearchReport,
    sources: list[Source],
    llm: LLM,
    *,
    budget: BudgetTracker | None = None,
    callbacks: list | None = None,
) -> FactualityReport:
    claims = _extract_claims(report)
    if not claims:
        return FactualityReport(score=0.0, notes="no checkable claims extracted")

    runnable = llm.structured(JudgeOutput, role="smart")
    result = await runnable.ainvoke(
        [
            ("system", JUDGE_SYSTEM),
            (
                "human",
                JUDGE_HUMAN.format(
                    sources=_sources_block(sources),
                    claims="\n".join(f"{i+1}. {c}" for i, c in enumerate(claims)),
                ),
            ),
        ],
        config={"callbacks": callbacks or []},
    )
    raw = result.get("raw") if isinstance(result, dict) else None
    parsed: JudgeOutput = result.get("parsed") if isinstance(result, dict) else result
    if budget is not None and raw is not None:
        meta = getattr(raw, "usage_metadata", None) or {}
        budget.record_llm(
            llm._model_id("smart"),  # noqa: SLF001
            int(meta.get("input_tokens", 0)),
            int(meta.get("output_tokens", 0)),
        )

    fr = _aggregate(parsed.verdicts if parsed else [])
    fr.notes = parsed.notes if parsed else "judge returned no output"
    return fr
