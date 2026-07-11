"""Pydantic schemas that form the data contract between agents.

These models are used both for structured LLM outputs (via
``with_structured_output``) and for passing typed data through the
LangGraph state.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------
class SubTopic(BaseModel):
    """A single research angle produced by the Planner."""

    title: str = Field(..., description="Concise sub-topic title.")
    rationale: str = Field(..., description="Why this sub-topic matters.")
    search_queries: list[str] = Field(
        default_factory=list,
        description="Concrete web-search queries for this sub-topic.",
    )


class ResearchPlan(BaseModel):
    """Structured research plan for a topic."""

    topic: str
    objective: str = Field(..., description="What a good final report must deliver.")
    sub_topics: list[SubTopic] = Field(default_factory=list)

    def all_queries(self) -> list[str]:
        """Flatten every search query across sub-topics."""

        return [q for st in self.sub_topics for q in st.search_queries]


# ---------------------------------------------------------------------------
# Search & collection
# ---------------------------------------------------------------------------
class SearchResult(BaseModel):
    """A single search hit returned by a search provider."""

    title: str
    url: str
    snippet: str = ""
    score: float | None = None
    provider: str = "unknown"
    query: str = ""


# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------
class ScrapedDocument(BaseModel):
    """Full-text content extracted from a source URL."""

    url: str
    title: str = ""
    content: str = ""
    word_count: int = 0
    success: bool = True
    error: str | None = None
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ---------------------------------------------------------------------------
# Reflection
# ---------------------------------------------------------------------------
class ReflectionResult(BaseModel):
    """Self-critique of the research gathered so far."""

    is_sufficient: bool = Field(
        ..., description="True if the evidence can support a complete report."
    )
    gaps: list[str] = Field(
        default_factory=list, description="Knowledge gaps still to be filled."
    )
    follow_up_queries: list[str] = Field(
        default_factory=list,
        description="New search queries to close the identified gaps.",
    )
    reasoning: str = ""


# ---------------------------------------------------------------------------
# Fact checking
# ---------------------------------------------------------------------------
class FactCheckVerdict(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    UNVERIFIABLE = "unverifiable"


class FactCheckResult(BaseModel):
    """Verification of a single claim against gathered sources."""

    claim: str
    verdict: FactCheckVerdict
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    supporting_urls: list[str] = Field(default_factory=list)
    explanation: str = ""


# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------
class Citation(BaseModel):
    """A numbered citation referenced in the final report."""

    index: int
    title: str
    url: str


class ReportStatus(str, Enum):
    """Terminal status of a research run."""

    OK = "ok"
    NO_RESULTS = "no_results"


class ResearchReport(BaseModel):
    """The final markdown research report and its metadata."""

    topic: str
    markdown: str
    status: ReportStatus = ReportStatus.OK
    citations: list[Citation] = Field(default_factory=list)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
