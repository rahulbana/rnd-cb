"""Request/response schemas and the shared option vocabulary."""

from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, Field

SummaryLength = Literal["short", "medium", "detailed"]
SummaryStyle = Literal[
    "neutral", "executive", "technical", "academic", "casual", "eli5"
]
SummaryFormat = Literal["paragraph", "bullets", "key-points", "structured"]

SUMMARY_LENGTHS: list[str] = list(get_args(SummaryLength))
SUMMARY_STYLES: list[str] = list(get_args(SummaryStyle))
SUMMARY_FORMATS: list[str] = list(get_args(SummaryFormat))


class SummarizeRequest(BaseModel):
    """Options for a summary request. Invalid enum values yield a 422 automatically."""

    text: str
    length: SummaryLength = "medium"
    style: SummaryStyle = "neutral"
    format: SummaryFormat = "paragraph"
    #: Optional free-text steer, e.g. "focus on the security implications".
    focus: str | None = None


class ExtractRequest(BaseModel):
    text: str


class StructuredSummary(BaseModel):
    """Machine-readable extraction result (also used as the Structured Outputs schema)."""

    title: str = Field(description="A concise title for the document.")
    summary: str = Field(description="A 2-4 sentence overview.")
    keyPoints: list[str] = Field(
        description="Most important takeaways, ordered by importance."
    )
    decisions: list[str] = Field(
        description="Decisions made or proposed (empty if none)."
    )
    actionItems: list[str] = Field(
        description="Concrete next steps, each starting with a verb (empty if none)."
    )
    entities: list[str] = Field(
        description="Notable people, orgs, products, or places mentioned."
    )
