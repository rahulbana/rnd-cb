"""Article CRUD schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.generation import NerTag, Source


class ArticleBase(BaseModel):
    title: str = Field(default="Untitled", max_length=512)
    body: str = ""
    summary: str = ""
    seo_description: str = ""
    keywords: list[str] = Field(default_factory=list)
    sentiment: str = "neutral"
    tags: list[str] = Field(default_factory=list)
    ner_tags: list[NerTag] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    banner_image: str | None = None
    trace_id: str | None = None
    status: str = "draft"
    prompt: str | None = None


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    """All fields optional — partial updates supported."""

    title: str | None = None
    body: str | None = None
    summary: str | None = None
    seo_description: str | None = None
    keywords: list[str] | None = None
    sentiment: str | None = None
    tags: list[str] | None = None
    ner_tags: list[NerTag] | None = None
    sources: list[Source] | None = None
    banner_image: str | None = None
    status: str | None = None
    prompt: str | None = None


class ArticleOut(ArticleBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


class ArticleListItem(BaseModel):
    """Lightweight representation for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    summary: str
    sentiment: str
    tags: list[str]
    banner_image: str | None = None
    status: str
    updated_at: datetime


class SearchResult(BaseModel):
    article: ArticleListItem
    score: float = Field(..., description="Similarity score (higher = closer)")
