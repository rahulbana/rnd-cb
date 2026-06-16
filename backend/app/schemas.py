"""Pydantic request/response models shared across the API.

These models double as the validation layer for incoming requests and as the
documented contract that the React frontend consumes.
"""
from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field, field_validator


class Language(str, Enum):
    """Programming languages the agent is allowed to generate code for.

    Keeping this as an enum means FastAPI rejects unknown languages with a
    clear 422 error before any work (or any OpenAI spend) happens, and the
    frontend dropdown can be populated from the same source of truth via
    ``GET /api/languages``.
    """

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    GO = "go"
    RUST = "rust"
    RUBY = "ruby"
    PHP = "php"
    KOTLIN = "kotlin"
    SWIFT = "swift"

    @property
    def display_name(self) -> str:
        """Human friendly label for the frontend dropdown."""
        return {
            Language.PYTHON: "Python",
            Language.JAVASCRIPT: "JavaScript",
            Language.TYPESCRIPT: "TypeScript",
            Language.JAVA: "Java",
            Language.C: "C",
            Language.CPP: "C++",
            Language.CSHARP: "C#",
            Language.GO: "Go",
            Language.RUST: "Rust",
            Language.RUBY: "Ruby",
            Language.PHP: "PHP",
            Language.KOTLIN: "Kotlin",
            Language.SWIFT: "Swift",
        }[self]


class GenerateRequest(BaseModel):
    """Payload sent by the frontend to request a generated solution."""

    language: Language = Field(
        ...,
        description="Target programming language selected in the dropdown.",
    )
    problem_statement: str = Field(
        ...,
        min_length=5,
        max_length=5000,
        description="Natural language description of the problem to solve.",
    )

    @field_validator("problem_statement")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Reject whitespace-only problem statements."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("problem_statement must not be empty.")
        return cleaned


class LanguageOption(BaseModel):
    """A single selectable language for the frontend dropdown."""

    value: str = Field(..., description="Enum value sent back on requests.")
    label: str = Field(..., description="Human readable label to display.")


class GenerateResponse(BaseModel):
    """The complete result of the multi-agent pipeline."""

    language: str = Field(..., description="The language the code was written in.")
    plan: List[str] = Field(
        ..., description="Ordered, step-by-step implementation plan."
    )
    code: str = Field(..., description="The final, reviewed source code.")
    review_notes: List[str] = Field(
        default_factory=list,
        description="Issues the reviewer agent found and fixed (or flagged).",
    )
    explanation: str = Field(
        default="",
        description="Short prose explanation of how the code works.",
    )
