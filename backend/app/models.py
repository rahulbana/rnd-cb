"""Pydantic schemas describing the analysis payload returned to the frontend."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# The semantic type the agent infers for each column. This is richer than the
# raw pandas dtype: it captures how a human analyst would *read* the column.
SemanticType = Literal[
    "integer",
    "float",
    "boolean",
    "categorical",
    "text",
    "datetime",
    "identifier",
    "constant",
    "empty",
]


class ColumnProfile(BaseModel):
    """A single column analysed from every relevant perspective."""

    name: str
    dtype: str
    semantic_type: SemanticType
    count: int
    missing: int
    missing_pct: float
    unique: int
    unique_pct: float

    # Numeric perspective (None for non-numeric columns).
    mean: float | None = None
    std: float | None = None
    min: float | None = None
    max: float | None = None
    median: float | None = None
    q1: float | None = None
    q3: float | None = None
    skew: float | None = None
    kurtosis: float | None = None
    zeros: int | None = None
    negatives: int | None = None
    outlier_count: int | None = None

    # Categorical / boolean / text perspective.
    top_values: list[dict[str, Any]] = Field(default_factory=list)
    true_count: int | None = None
    false_count: int | None = None
    avg_length: float | None = None

    # Datetime perspective.
    min_date: str | None = None
    max_date: str | None = None

    # Per-column human readable notes from the heuristic layer.
    notes: list[str] = Field(default_factory=list)

    # Distribution histogram bins (numeric columns) for the frontend charts.
    histogram: dict[str, list[float]] | None = None


class ChartSpec(BaseModel):
    """A declarative chart description the React frontend knows how to render."""

    id: str
    type: Literal["bar", "histogram", "line", "pie", "scatter", "heatmap"]
    title: str
    description: str
    # x/y key names inside `data`, plus the data array itself.
    x_key: str | None = None
    y_keys: list[str] = Field(default_factory=list)
    data: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class Correlation(BaseModel):
    column_a: str
    column_b: str
    coefficient: float
    strength: str
    direction: str


class DatasetOverview(BaseModel):
    filename: str
    rows: int
    columns: int
    total_cells: int
    missing_cells: int
    missing_pct: float
    duplicate_rows: int
    memory_kb: float
    type_breakdown: dict[str, int]


class AnalysisResponse(BaseModel):
    """The full payload powering the dashboard."""

    overview: DatasetOverview
    columns: list[ColumnProfile]
    correlations: list[Correlation]
    charts: list[ChartSpec]
    inferences: list[str]
    narrative: str
    suggested_questions: list[str]
    llm_used: bool
    sample_rows: list[dict[str, Any]]
