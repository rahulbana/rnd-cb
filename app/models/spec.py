"""Pydantic models describing a dataset generation plan.

The :class:`DatasetSpec` is the central contract of the system. The Planner
agent produces one from a natural-language prompt, and every downstream agent
reads and/or refines it. Keeping the spec fully declarative means a generation
run is reproducible from ``(spec, seed)`` alone.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class TaskType(str, Enum):
    """Supervised / unsupervised task the dataset targets."""

    BINARY_CLASSIFICATION = "binary_classification"
    MULTICLASS_CLASSIFICATION = "multiclass_classification"
    MULTILABEL_CLASSIFICATION = "multilabel_classification"
    REGRESSION = "regression"
    MULTIOUTPUT_REGRESSION = "multioutput_regression"
    CLUSTERING = "clustering"
    TIME_SERIES = "time_series"

    @property
    def is_classification(self) -> bool:
        return self in {
            TaskType.BINARY_CLASSIFICATION,
            TaskType.MULTICLASS_CLASSIFICATION,
            TaskType.MULTILABEL_CLASSIFICATION,
        }

    @property
    def is_regression(self) -> bool:
        return self in {TaskType.REGRESSION, TaskType.MULTIOUTPUT_REGRESSION}

    @property
    def is_supervised(self) -> bool:
        return self.is_classification or self.is_regression or self == TaskType.TIME_SERIES


class DType(str, Enum):
    """Logical column type. Maps onto concrete pandas dtypes at build time."""

    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    CATEGORY = "category"
    ORDINAL = "ordinal"
    DATETIME = "datetime"
    UUID = "uuid"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    NAME = "name"
    TEXT = "text"


class Distribution(str, Enum):
    """Supported numeric distributions."""

    NORMAL = "normal"
    UNIFORM = "uniform"
    POISSON = "poisson"
    GAMMA = "gamma"
    EXPONENTIAL = "exponential"
    LOGNORMAL = "lognormal"
    BETA = "beta"
    POWERLAW = "powerlaw"


class FeatureRole(str, Enum):
    ID = "id"
    FEATURE = "feature"
    TARGET = "target"
    TIME = "time"


class FeatureSpec(BaseModel):
    """Declarative description of a single column."""

    name: str
    dtype: DType = DType.FLOAT
    role: FeatureRole = FeatureRole.FEATURE

    # Numeric knobs.
    distribution: Distribution = Distribution.NORMAL
    params: dict[str, float] = Field(default_factory=dict)
    low: float | None = None
    high: float | None = None

    # Categorical knobs.
    categories: list[str] | None = None
    weights: list[float] | None = None

    # Datetime knobs (ISO strings).
    start: str | None = None
    end: str | None = None

    # A short human description surfaced in the data dictionary.
    description: str = ""

    @model_validator(mode="after")
    def _check_categories(self) -> "FeatureSpec":
        if self.weights is not None and self.categories is not None:
            if len(self.weights) != len(self.categories):
                raise ValueError(
                    f"feature '{self.name}': weights/categories length mismatch"
                )
        return self


class CorrelationSpec(BaseModel):
    """A desired linear relationship between two numeric features."""

    source: str
    target: str
    strength: float = Field(0.5, ge=-1.0, le=1.0)


class TargetSpec(BaseModel):
    """How the target/label column is synthesised."""

    name: str = "target"
    # For classification: probability of the positive class (binary) or the
    # per-class distribution (multiclass). For regression this is unused.
    positive_rate: float = 0.5
    n_classes: int = 2
    class_names: list[str] | None = None
    # Fraction of the label driven by signal vs. noise (0..1).
    signal_strength: float = Field(0.7, ge=0.0, le=1.0)
    # Regression target scale.
    noise: float = 0.1
    nonlinear: bool = False


class QualitySpec(BaseModel):
    """Controlled data-quality degradations to inject."""

    missing_rate: float = Field(0.0, ge=0.0, le=1.0)
    duplicate_rate: float = Field(0.0, ge=0.0, le=1.0)
    outlier_rate: float = Field(0.0, ge=0.0, le=1.0)
    typo_rate: float = Field(0.0, ge=0.0, le=1.0)
    noise: float = Field(0.0, ge=0.0, le=1.0)


class DatasetSpec(BaseModel):
    """Full, reproducible description of a dataset to be generated."""

    name: str = "dataset"
    description: str = ""
    domain: str = "generic"
    task_type: TaskType = TaskType.BINARY_CLASSIFICATION
    n_rows: int = Field(1000, ge=1)

    features: list[FeatureSpec] = Field(default_factory=list)
    target: TargetSpec | None = None
    correlations: list[CorrelationSpec] = Field(default_factory=list)
    quality: QualitySpec = Field(default_factory=QualitySpec)

    random_seed: int = 42

    # Free-form metadata carried from the planner (original prompt, hints...).
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def numeric_features(self) -> list[FeatureSpec]:
        return [
            f
            for f in self.features
            if f.dtype in {DType.FLOAT, DType.INTEGER}
            and f.role == FeatureRole.FEATURE
        ]

    @property
    def feature_names(self) -> list[str]:
        return [f.name for f in self.features]

    def get_feature(self, name: str) -> FeatureSpec | None:
        for f in self.features:
            if f.name == name:
                return f
        return None
