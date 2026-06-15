"""Pydantic request/response schemas."""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Platform(str, Enum):
    linkedin = "linkedin"
    website = "website"
    blog = "blog"


class Tone(str, Enum):
    professional = "professional"
    casual = "casual"
    friendly = "friendly"
    authoritative = "authoritative"
    inspirational = "inspirational"
    witty = "witty"


class Length(str, Enum):
    short = "short"
    medium = "medium"
    long = "long"


class GenerateRequest(BaseModel):
    topic: str = Field(default="", description="Seed topic or interest. Leave blank to let the agent pick a trend.")
    platform: Platform = Platform.linkedin
    tone: Tone = Tone.professional
    length: Length = Length.medium
    audience: str = Field(default="", description="Target audience, e.g. 'startup founders'.")
    preferences: str = Field(default="", description="Extra preferences/instructions for the writer.")


class Source(BaseModel):
    title: str
    url: str
    snippet: str = ""
    published: Optional[str] = None


class VerificationResult(BaseModel):
    approved: bool = True
    score: float = 0.0
    issues: list[str] = []
    notes: str = ""


class ContentResponse(BaseModel):
    id: str
    topic: str
    platform: str
    tone: str
    length: str
    audience: str
    preferences: str
    title: str
    body: str
    description: str
    keywords: list[str]
    hashtags: list[str]
    trending_topic: str
    sources: list[Source]
    verification: VerificationResult
    status: str
    created_at: Optional[str] = None
