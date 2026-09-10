"""Pydantic request/response models for the API."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural-language question.")
    schema_text: str = Field(
        "",
        description="Database schema as DDL or a plain-text description.",
    )
    dialect: str | None = Field(
        None, description="SQL dialect override (e.g. postgres, mysql, sqlite)."
    )


class GenerateResponse(BaseModel):
    sql: str = Field(..., description="Formatted, read-only SQL query.")
    explanation: str = Field("", description="Plain-language explanation of the query.")
    tables_used: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    validation: "ValidationResult"
    history_id: int | None = None


# ---------------------------------------------------------------------------
# Explanation
# ---------------------------------------------------------------------------
class ExplainRequest(BaseModel):
    sql: str = Field(..., min_length=1)
    schema_text: str = ""
    dialect: str | None = None


class ExplainResponse(BaseModel):
    explanation: str


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
class FormatRequest(BaseModel):
    sql: str = Field(..., min_length=1)
    dialect: str | None = None


class FormatResponse(BaseModel):
    sql: str


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
class ValidateRequest(BaseModel):
    sql: str = Field(..., min_length=1)
    dialect: str | None = None


class ValidationResult(BaseModel):
    valid: bool
    read_only: bool
    statement_type: str | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
class HistoryItem(BaseModel):
    id: int
    question: str
    sql: str
    explanation: str
    dialect: str
    valid: bool
    created_at: datetime


class HistoryList(BaseModel):
    items: list[HistoryItem]
    total: int


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: Literal["ok"]
    llm_configured: bool
    model: str
    dialect: str


GenerateResponse.model_rebuild()
