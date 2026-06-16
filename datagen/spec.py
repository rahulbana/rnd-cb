"""Specification objects for the data generation agent.

A *spec* is a plain dictionary (typically loaded from JSON/YAML or built in
Python) that fully describes the dataset to generate.  These dataclasses give
the spec a validated, typed shape and convenient ``from_dict`` parsers so the
rest of the package never has to second-guess user input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Column data types understood by the generator.
NUMERIC_TYPES = {"int", "float"}
SUPPORTED_DTYPES = NUMERIC_TYPES | {
    "category",
    "bool",
    "datetime",
    "text",
    "uuid",
    "name",
    "email",
}

# Task types understood by the agent.
SUPPORTED_TASKS = {
    "tabular",
    "classification",
    "regression",
    "clustering",
    "text_classification",
    "summarization",
}


class SpecError(ValueError):
    """Raised when a user-supplied spec is invalid."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SpecError(message)


@dataclass
class ColumnSpec:
    """Describes a single column to generate.

    Attributes:
        name: Column name.
        dtype: One of :data:`SUPPORTED_DTYPES`.
        distribution: Sampling distribution for numeric columns
            (``uniform``, ``normal``, ``lognormal``, ``exponential``).
        min: Lower bound (numeric / datetime start).
        max: Upper bound (numeric / datetime end).
        mean: Mean for ``normal``/``lognormal`` distributions.
        std: Standard deviation for ``normal``/``lognormal`` distributions.
        categories: Allowed values for ``category`` columns.
        weights: Optional sampling weights aligned with ``categories``.
        p_true: Probability of ``True`` for ``bool`` columns.
        decimals: Rounding precision for ``float`` columns.
        datetime_format: ``strftime`` format for ``datetime`` columns.
        outlier_pct: Fraction (0..1) of values replaced by outliers.
        null_pct: Fraction (0..1) of values set to null/NaN.
        text_words: (min, max) word count for ``text`` columns.
    """

    name: str
    dtype: str = "float"
    distribution: str = "uniform"
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    std: float | None = None
    categories: list[Any] | None = None
    weights: list[float] | None = None
    p_true: float = 0.5
    decimals: int = 2
    datetime_format: str | None = None
    outlier_pct: float = 0.0
    null_pct: float = 0.0
    text_words: tuple[int, int] = (8, 24)

    def __post_init__(self) -> None:
        _require(bool(self.name), "Column 'name' is required.")
        _require(
            self.dtype in SUPPORTED_DTYPES,
            f"Column '{self.name}': unsupported dtype '{self.dtype}'. "
            f"Choose from {sorted(SUPPORTED_DTYPES)}.",
        )
        _require(
            0.0 <= self.outlier_pct <= 1.0,
            f"Column '{self.name}': outlier_pct must be between 0 and 1.",
        )
        _require(
            0.0 <= self.null_pct <= 1.0,
            f"Column '{self.name}': null_pct must be between 0 and 1.",
        )
        if self.dtype in NUMERIC_TYPES and self.distribution == "uniform":
            # Provide sensible defaults so a bare numeric column still works.
            if self.min is None:
                self.min = 0.0
            if self.max is None:
                self.max = 1.0
            _require(
                self.min <= self.max,
                f"Column '{self.name}': min ({self.min}) must be <= max ({self.max}).",
            )
        if self.dtype == "category":
            _require(
                bool(self.categories),
                f"Column '{self.name}': 'categories' is required for category dtype.",
            )
            if self.weights is not None:
                _require(
                    len(self.weights) == len(self.categories),
                    f"Column '{self.name}': weights length must match categories.",
                )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ColumnSpec":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        unknown = set(data) - known
        _require(
            not unknown,
            f"Column '{data.get('name', '?')}': unknown keys {sorted(unknown)}.",
        )
        payload = dict(data)
        if "text_words" in payload and isinstance(payload["text_words"], list):
            payload["text_words"] = tuple(payload["text_words"])
        return cls(**payload)


@dataclass
class DatasetSpec:
    """Top-level description of a dataset to generate.

    Attributes:
        task: One of :data:`SUPPORTED_TASKS`.
        n_rows: Number of records to generate.
        columns: Explicit feature columns (optional for synthetic tasks).
        n_features: Number of auto-generated numeric features for
            classification/regression/clustering tasks.
        n_classes: Number of classes for classification.
        n_clusters: Number of clusters for clustering.
        cluster_std: Spread of each cluster (clustering / classification).
        noise: Gaussian noise added to regression targets.
        target_name: Name of the generated target column.
        class_names: Optional human-readable class labels.
        n_informative: Informative feature count for regression.
        feature_outlier_pct: Fraction (0..1) of values in each auto-generated
            numeric feature column replaced by outliers.
        text: Text-task configuration (see :mod:`datagen.text`).
        seed: Random seed for reproducibility.
    """

    task: str = "tabular"
    n_rows: int = 100
    columns: list[ColumnSpec] = field(default_factory=list)
    n_features: int = 5
    n_classes: int = 2
    n_clusters: int = 3
    cluster_std: float = 1.0
    noise: float = 1.0
    target_name: str = "target"
    class_names: list[str] | None = None
    n_informative: int | None = None
    feature_outlier_pct: float = 0.0
    text: dict[str, Any] = field(default_factory=dict)
    seed: int | None = None

    def __post_init__(self) -> None:
        _require(
            self.task in SUPPORTED_TASKS,
            f"Unsupported task '{self.task}'. Choose from {sorted(SUPPORTED_TASKS)}.",
        )
        _require(self.n_rows > 0, "n_rows must be positive.")
        _require(
            0.0 <= self.feature_outlier_pct <= 1.0,
            "feature_outlier_pct must be between 0 and 1.",
        )
        if self.task == "classification":
            _require(self.n_classes >= 2, "classification needs n_classes >= 2.")
            if self.class_names is not None:
                _require(
                    len(self.class_names) == self.n_classes,
                    "class_names length must match n_classes.",
                )
        if self.task == "clustering":
            _require(self.n_clusters >= 1, "clustering needs n_clusters >= 1.")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DatasetSpec":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        unknown = set(data) - known
        _require(not unknown, f"Unknown spec keys: {sorted(unknown)}.")
        payload = dict(data)
        payload["columns"] = [
            ColumnSpec.from_dict(c) for c in payload.get("columns", [])
        ]
        return cls(**payload)
