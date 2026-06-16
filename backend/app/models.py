"""Pydantic schemas shared across the agent pipeline and the API."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class ReviewerType(str, Enum):
    """Category of the person/entity behind a review."""

    reader = "reader"
    critic = "critic"
    company = "company"
    celebrity = "celebrity"
    unknown = "unknown"


class Sentiment(str, Enum):
    positive = "positive"
    mixed = "mixed"
    negative = "negative"
    unknown = "unknown"


class SearchResult(BaseModel):
    """A single raw web search hit fed into the agents."""

    title: str = ""
    url: str = ""
    content: str = ""


class BookInfo(BaseModel):
    """Core facts and summary about the book."""

    title: str
    author: str = "Unknown"
    published_year: int | None = None
    genres: list[str] = Field(default_factory=list)
    summary: str = ""


class Review(BaseModel):
    """A single aggregated review attributed to a source."""

    reviewer_name: str
    reviewer_type: ReviewerType = ReviewerType.unknown
    source: str = ""
    source_url: str = ""
    rating: float | None = None  # normalized 0-5 when available
    sentiment: Sentiment = Sentiment.unknown
    excerpt: str = ""


class VerificationResult(BaseModel):
    """Output of the verifier agent's sanity check."""

    verified: bool = False
    confidence: float = 0.0  # 0..1
    notes: str = ""
    flagged_claims: list[str] = Field(default_factory=list)


class BookReport(BaseModel):
    """The full assembled report returned to the client."""

    book: BookInfo
    reviews: list[Review] = Field(default_factory=list)
    verification: VerificationResult = Field(default_factory=VerificationResult)
    sources: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ---- API request/response models ----


class AnalyzeRequest(BaseModel):
    title: str = Field(..., min_length=1, description="Book title to research")
    author: str | None = Field(
        default=None, description="Optional author hint to disambiguate"
    )


class ExportFormat(str, Enum):
    markdown = "markdown"
    pdf = "pdf"
