"""Planner agent — stage 1.

Turns a high-level request ("CBSE Class 10 English previous year papers") into a
concrete plan: precise interpretation, the web searches to run, the sources most
likely to be authentic, and the acceptance criteria later stages check against.
"""

from __future__ import annotations

from ..llm import LLMClient
from ..models import PaperRequest, SearchPlan

_SYSTEM = """You are the planning agent in a system that collects authentic
board examination question papers for Indian school boards (CBSE, ICSE/CISCE,
UP Board, and similar state boards).

Your job is NOT to find papers yet. Your job is to produce a precise, practical
search plan. Be specific about Indian education context:

- Distinguish boards correctly (CBSE vs ICSE/CISCE vs UP Board / UPMSP, etc.).
- Prefer official and reputable sources: the board's own site (cbse.gov.in,
  cisce.org, upmsp.edu.in), and well-known education portals.
- Account for the subject and class exactly as requested.
- If specific years are requested, target each; otherwise target recent years.
- Write acceptance criteria that a downstream validator can mechanically check
  (correct board, subject, class, plausible year, looks like a real paper).

Produce 4-8 focused search queries that together cover the request well."""


class PlannerAgent:
    """Produces a :class:`SearchPlan` from a :class:`PaperRequest`."""

    name = "planner"

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def run(self, request: PaperRequest) -> SearchPlan:
        user = (
            "Create a search plan for this request:\n"
            f"- Board: {request.board}\n"
            f"- Subject: {request.subject}\n"
            f"- Class: {request.klass}\n"
            f"- Paper type: {request.paper_type}\n"
            f"- Years: {request.years or 'recent years'}\n"
            f"- Target count: {request.max_papers}\n"
        )
        return self._llm.parse(system=_SYSTEM, user=user, schema=SearchPlan)
