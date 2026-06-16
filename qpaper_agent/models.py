"""Typed data structures shared between the agents.

Pydantic models double as the JSON schemas that the OpenAI structured-output
API uses, so the same definitions describe both the in-process data and the
contract we ask the LLM to fill in.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class PaperRequest(BaseModel):
    """What the user is asking for."""

    board: str = Field(description="Examination board, e.g. CBSE, ICSE, UP Board.")
    subject: str = Field(description="Subject, e.g. English, Hindi, Mathematics.")
    klass: str = Field(description="Class / grade, e.g. '10' or '12'.")
    paper_type: str = Field(
        default="previous year question papers",
        description="Kind of papers wanted, e.g. previous year, sample, model.",
    )
    years: List[int] = Field(
        default_factory=list,
        description="Specific years to target. Empty means recent years.",
    )
    max_papers: int = Field(
        default=10, description="Maximum number of papers to download."
    )

    def describe(self) -> str:
        """Human-readable one-line summary used in prompts and logs."""
        years = ", ".join(str(y) for y in self.years) if self.years else "recent years"
        return (
            f"{self.board} Class {self.klass} {self.subject} "
            f"{self.paper_type} ({years})"
        )


class SearchQuery(BaseModel):
    """A single web search the planner wants the search agent to run."""

    query: str = Field(description="The exact text to search the web for.")
    rationale: str = Field(description="Why this query helps satisfy the request.")


class SearchPlan(BaseModel):
    """The planner's output: how to go about finding the papers."""

    interpreted_request: str = Field(
        description="Restatement of the request in precise terms."
    )
    queries: List[SearchQuery] = Field(
        description="Ordered list of web searches to perform."
    )
    trusted_sources: List[str] = Field(
        default_factory=list,
        description="Domains likely to host authentic papers (official boards, "
        "reputable education portals).",
    )
    acceptance_criteria: List[str] = Field(
        description="Checklist a candidate must satisfy to count as a match."
    )


class PaperCandidate(BaseModel):
    """A potential question paper discovered on the web."""

    title: str = Field(description="Human-readable title of the paper.")
    url: str = Field(description="Direct URL to the paper or its download page.")
    source: str = Field(description="Hosting site / domain.")
    board: Optional[str] = Field(default=None, description="Detected board.")
    subject: Optional[str] = Field(default=None, description="Detected subject.")
    klass: Optional[str] = Field(default=None, description="Detected class.")
    year: Optional[int] = Field(default=None, description="Detected year, if known.")
    is_pdf: bool = Field(
        default=False, description="True if the URL points straight at a PDF."
    )
    notes: str = Field(default="", description="Anything noteworthy about the find.")


class SearchResult(BaseModel):
    """Container for everything the search agent surfaced."""

    candidates: List[PaperCandidate] = Field(default_factory=list)


class ValidatedPaper(BaseModel):
    """A candidate after the validator has judged it."""

    candidate: PaperCandidate
    is_valid: bool = Field(description="Does this genuinely match the request?")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Validator confidence between 0 and 1."
    )
    reason: str = Field(description="Why it was accepted or rejected.")


class ValidationReport(BaseModel):
    """The validator's full assessment."""

    results: List[ValidatedPaper] = Field(default_factory=list)


class DownloadResult(BaseModel):
    """Outcome of attempting to download one paper."""

    title: str
    url: str
    path: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    bytes_written: int = 0
