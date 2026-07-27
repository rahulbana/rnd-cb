"""Feature agent: materialise each column's base values.

This agent draws every feature independently from its declared distribution.
Cross-feature structure (correlations) and the label are added by later agents,
which keeps each stage single-purpose and easy to test.
"""

from __future__ import annotations

import uuid

import numpy as np
import pandas as pd

from app.agents.base import Agent
from app.models.spec import DatasetSpec, DType, FeatureRole, FeatureSpec
from app.utils.rng import sample_distribution

try:  # Faker is used for realistic PII-like columns when available.
    from faker import Faker

    _FAKER = Faker()
    Faker.seed(0)
except Exception:  # pragma: no cover - optional dependency
    _FAKER = None


class FeatureAgent(Agent):
    name = "feature"

    def run(self, spec: DatasetSpec, rng: np.random.Generator) -> pd.DataFrame:
        n = spec.n_rows
        columns: dict[str, np.ndarray | list] = {}
        for feature in spec.features:
            columns[feature.name] = self._build_column(feature, n, rng)
        df = pd.DataFrame(columns)
        self.log(f"generated {df.shape[0]} rows x {df.shape[1]} base columns")
        return df

    def _build_column(self, f: FeatureSpec, n: int, rng: np.random.Generator):
        if f.role == FeatureRole.ID and f.dtype == DType.INTEGER:
            return np.arange(1, n + 1)

        if f.dtype in {DType.FLOAT, DType.INTEGER}:
            return self._numeric(f, n, rng)
        if f.dtype in {DType.CATEGORY, DType.ORDINAL}:
            return self._categorical(f, n, rng)
        if f.dtype == DType.BOOLEAN:
            return rng.random(n) < 0.5
        if f.dtype == DType.DATETIME:
            return self._datetime(f, n, rng)
        if f.dtype == DType.UUID:
            return [str(uuid.UUID(int=int(x))) for x in rng.integers(0, 2**63, n)]
        if f.dtype in {DType.EMAIL, DType.PHONE, DType.URL, DType.NAME, DType.TEXT}:
            return self._faker_column(f, n, rng)
        # Fallback.
        return rng.normal(0, 1, n)

    def _numeric(self, f: FeatureSpec, n: int, rng: np.random.Generator) -> np.ndarray:
        values = sample_distribution(rng, f.distribution.value, n, f.params)
        if f.low is not None:
            values = np.maximum(values, f.low)
        if f.high is not None:
            values = np.minimum(values, f.high)
        if f.dtype == DType.INTEGER:
            values = np.round(values).astype(np.int64)
        else:
            values = np.round(values, 4)
        return values

    def _categorical(self, f: FeatureSpec, n: int, rng: np.random.Generator):
        categories = f.categories or ["a", "b", "c"]
        p = f.weights if f.weights else None
        return rng.choice(categories, size=n, p=p)

    def _datetime(self, f: FeatureSpec, n: int, rng: np.random.Generator):
        start = pd.Timestamp(f.start or "2022-01-01")
        end = pd.Timestamp(f.end or "2024-12-31")
        span = (end - start).total_seconds()
        offsets = rng.uniform(0, span, n)
        return start + pd.to_timedelta(offsets, unit="s")

    def _faker_column(self, f: FeatureSpec, n: int, rng: np.random.Generator):
        if _FAKER is None:
            return [f"{f.dtype.value}_{i}" for i in range(n)]
        gen = {
            DType.EMAIL: _FAKER.email,
            DType.PHONE: _FAKER.phone_number,
            DType.URL: _FAKER.url,
            DType.NAME: _FAKER.name,
            DType.TEXT: lambda: _FAKER.sentence(nb_words=8),
        }[f.dtype]
        return [gen() for _ in range(n)]
