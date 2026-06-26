"""Domain models for search results and sources."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class RawResult(BaseModel):
    """A single raw result returned by a search provider."""

    title: str = ""
    url: str = ""
    content: str = ""


class Source(RawResult):
    """A result enriched with the sub-query that produced it."""

    subquery: str = ""


class SearchResult(BaseModel):
    """All sources gathered for one sub-query."""

    subquery: str
    sources: List[Source] = Field(default_factory=list)
