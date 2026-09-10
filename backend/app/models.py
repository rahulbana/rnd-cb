"""Pydantic request/response models for the API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Request payload for the /api/generate endpoint."""

    prompt: str = Field(
        ...,
        min_length=1,
        description="Natural-language description of the data to generate.",
        examples=[
            "Create a customer named Rahul, email rahul@example.com, "
            "age 35, and city Delhi."
        ],
    )
    schema_: dict[str, Any] | None = Field(
        default=None,
        alias="schema",
        description="Optional JSON Schema the generated JSON must satisfy.",
    )

    model_config = {"populate_by_name": True}


class ValidationErrorItem(BaseModel):
    """A single JSON Schema validation error."""

    path: str = Field(description="Dotted path to the offending field.")
    message: str = Field(description="Human-readable description of the error.")


class GenerateResponse(BaseModel):
    """Response payload for the /api/generate endpoint."""

    data: dict[str, Any] | list[Any] | None = Field(
        default=None, description="The generated (and possibly corrected) JSON."
    )
    valid: bool = Field(
        description="Whether the JSON validated against the provided schema."
    )
    attempts: int = Field(
        description="Number of LLM calls made (1 = correct on first try)."
    )
    errors: list[ValidationErrorItem] = Field(
        default_factory=list,
        description="Remaining validation errors, if any.",
    )
    raw_output: str | None = Field(
        default=None,
        description="Raw model output for the final attempt (useful for debugging).",
    )


class ValidateRequest(BaseModel):
    """Request payload for the /api/validate endpoint."""

    data: Any = Field(description="The JSON value to validate.")
    schema_: dict[str, Any] = Field(
        alias="schema", description="JSON Schema to validate against."
    )

    model_config = {"populate_by_name": True}


class ValidateResponse(BaseModel):
    """Response payload for the /api/validate endpoint."""

    valid: bool
    errors: list[ValidationErrorItem] = Field(default_factory=list)
