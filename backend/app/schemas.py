"""Pydantic request/response models for the writing assistant API."""
from enum import Enum

from pydantic import BaseModel, Field


class Action(str, Enum):
    """Supported text transformations."""

    GRAMMAR = "grammar"           # Fix grammar mistakes
    SPELLING = "spelling"         # Fix spelling mistakes
    IMPROVE = "improve"           # Improve clarity/flow of a sentence
    PROFESSIONAL = "professional" # Rewrite in a professional tone
    SIMPLIFY = "simplify"         # Make the text simpler / easier to read
    FORMAL = "formal"             # Convert to a formal register
    INFORMAL = "informal"         # Convert to an informal/casual register


class TransformRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000,
                      description="The text to transform.")
    action: Action = Field(..., description="Which transformation to apply.")


class Change(BaseModel):
    """A single edit the model made, for the before/after comparison."""

    original: str = Field(..., description="Original fragment.")
    replacement: str = Field(..., description="What it became.")
    reason: str = Field(..., description="Short explanation of the edit.")


class TransformResponse(BaseModel):
    action: Action
    original: str
    result: str = Field(..., description="The transformed text.")
    changes: list[Change] = Field(
        default_factory=list,
        description="List of notable edits between original and result.",
    )
    summary: str = Field("", description="One-line summary of what changed.")


class HealthResponse(BaseModel):
    status: str
    model: str
    openai_configured: bool
