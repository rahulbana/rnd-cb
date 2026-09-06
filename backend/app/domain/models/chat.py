"""Chat and generation domain models.

These are the internal, provider-neutral shapes for messages and LLM
responses. Adapters translate between these and provider SDK payloads.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Role(StrEnum):
    """Conversation roles, provider-agnostic."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """A single turn in a conversation."""

    role: Role
    content: str


class Citation(BaseModel):
    """A grounding reference tying an answer to a source chunk."""

    chunk_id: str
    document_id: str
    page: int | None = None
    heading_path: str | None = None
    score: float | None = None


class LLMResponse(BaseModel):
    """A completed (non-streamed) generation result."""

    content: str
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    citations: list[Citation] = Field(default_factory=list)
