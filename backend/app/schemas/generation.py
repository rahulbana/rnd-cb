"""Schemas for the LLM content-generation flow."""
from __future__ import annotations

from pydantic import BaseModel, Field


class NerTag(BaseModel):
    text: str = Field(..., description="The entity mention text")
    type: str = Field(..., description="Entity type, e.g. PERSON, ORG, LOCATION, DATE")


class Source(BaseModel):
    """A resource the content was drawn from or references."""

    title: str = Field(..., description="Name/title of the source")
    url: str | None = Field(
        default=None, description="Link to the source, if a reliable one is known"
    )
    type: str = Field(
        default="reference",
        description="reference | internal | dataset | quote | website",
    )
    snippet: str | None = Field(
        default=None, description="Optional note or excerpt explaining relevance"
    )


class GenerationRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=3,
        description="What the writer wants to write about.",
    )
    tone: str | None = Field(
        default=None, description="e.g. professional, casual, witty"
    )
    audience: str | None = Field(
        default=None, description="Target audience, e.g. developers, marketers"
    )
    length: str | None = Field(
        default="medium", description="short | medium | long"
    )
    keywords: list[str] = Field(
        default_factory=list, description="SEO keywords to weave in"
    )
    use_rag: bool = Field(
        default=True,
        description="Retrieve the writer's similar past articles as style context.",
    )
    use_web_search: bool = Field(
        default=False,
        description="Research the live web and ground the article in real sources.",
    )
    research_depth: str = Field(
        default="deep",
        description="quick (single search) | deep (multi-query research)",
    )


class GeneratedContent(BaseModel):
    """Structured content returned by the LLM (also used as the JSON schema).

    All fields have defaults so an occasional missing key from the model
    never fails validation or loses the rest of the generation; the service
    backfills sensible values (e.g. summary from the body).
    """

    title: str = Field(default="Untitled")
    body: str = Field(default="", description="Full article body in Markdown")
    summary: str = Field(default="", description="A short 1-2 sentence summary")
    seo_description: str = Field(
        default="", description="Meta description for SEO, ~155 chars"
    )
    keywords: list[str] = Field(default_factory=list)
    sentiment: str = Field(
        default="neutral", description="positive | neutral | negative"
    )
    tags: list[str] = Field(default_factory=list)
    ner_tags: list[NerTag] = Field(default_factory=list)
    sources: list[Source] = Field(
        default_factory=list,
        description=(
            "References the article draws on. Include real, well-known "
            "sources; only add a URL when confident it is correct."
        ),
    )


class ExpandRequest(BaseModel):
    title: str = Field(default="", description="Article title for context")
    body: str = Field(..., min_length=1, description="Current Markdown body to expand")
    mode: str = Field(
        default="longer",
        description="longer | examples | faq | depth | custom",
    )
    instruction: str | None = Field(
        default=None, description="Extra guidance (used with mode=custom)"
    )


class ExpandResponse(BaseModel):
    body: str


class DuplicateHit(BaseModel):
    article_id: str
    title: str
    distance: float


class GenerationResponse(BaseModel):
    content: GeneratedContent
    context_used: list[str] = Field(
        default_factory=list,
        description="IDs of past articles used as RAG context.",
    )
    possible_duplicates: list[DuplicateHit] = Field(default_factory=list)
    research_queries: list[str] = Field(
        default_factory=list,
        description="Web search queries run during deep research.",
    )
    trace_id: str | None = Field(
        default=None, description="Langfuse trace id for feedback/scoring."
    )


class FeedbackRequest(BaseModel):
    trace_id: str
    name: str = Field(default="user_rating", description="Score name")
    value: float = Field(..., description="Score value, e.g. 1 (up) / 0 (down)")
    comment: str | None = None
