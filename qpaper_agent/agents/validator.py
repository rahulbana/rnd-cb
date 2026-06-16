"""Validator agent — stage 3.

Judges each candidate against the request and the planner's acceptance criteria,
returning a verdict plus confidence. Only candidates it accepts move on to the
downloader, so this is the system's quality gate.
"""

from __future__ import annotations

from ..llm import LLMClient
from ..models import PaperRequest, SearchPlan, SearchResult, ValidationReport

_SYSTEM = """You are the validation agent. You receive candidate question papers
and must decide which genuinely match the request.

For each candidate, check that:
- the board matches (CBSE != ICSE != UP Board, etc.),
- the subject matches the requested subject,
- the class/grade matches,
- the year is plausible and, if specific years were requested, is one of them,
- it actually looks like a question paper (not syllabus, results, notes, or an
  unrelated page),
- the URL is concrete enough to download.

Be strict: when board/subject/class clearly conflict, reject. When the evidence
is ambiguous, accept only with low confidence and say what is uncertain. Return
a verdict, a confidence between 0 and 1, and a short reason for every candidate."""


class ValidatorAgent:
    """Filters candidates down to those that truly match the request."""

    name = "validator"

    def __init__(self, llm: LLMClient, min_confidence: float = 0.5) -> None:
        self._llm = llm
        self._min_confidence = min_confidence

    def run(
        self,
        request: PaperRequest,
        plan: SearchPlan,
        search: SearchResult,
    ) -> ValidationReport:
        if not search.candidates:
            return ValidationReport(results=[])

        criteria = "\n".join(f"- {c}" for c in plan.acceptance_criteria)
        candidates = "\n".join(
            f"{i + 1}. title={c.title!r} url={c.url} source={c.source} "
            f"board={c.board} subject={c.subject} class={c.klass} year={c.year}"
            for i, c in enumerate(search.candidates)
        )
        user = (
            f"Request: {request.describe()}\n\n"
            f"Acceptance criteria:\n{criteria}\n\n"
            f"Candidates:\n{candidates}\n\n"
            "Assess every candidate. Preserve the candidate's identifying "
            "fields in your output."
        )
        report = self._llm.parse(system=_SYSTEM, user=user, schema=ValidationReport)
        return report

    def accepted(self, report: ValidationReport):
        """Validated papers that pass the confidence threshold, best first."""
        passed = [
            r
            for r in report.results
            if r.is_valid and r.confidence >= self._min_confidence
        ]
        return sorted(passed, key=lambda r: r.confidence, reverse=True)
