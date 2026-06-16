"""Per-column value generation.

Each function turns a :class:`~datagen.spec.ColumnSpec` plus a NumPy random
generator into a 1-D array of values.  Outlier injection and null injection are
applied afterwards by :func:`generate_column`.
"""

from __future__ import annotations

import uuid as _uuid

import numpy as np
import pandas as pd

from .outliers import inject_outliers
from .spec import ColumnSpec
from .text import random_sentences

_FIRST_NAMES = [
    "Aarav", "Bianca", "Chen", "Diego", "Elena", "Farah", "Grace", "Hiro",
    "Imani", "Julia", "Kabir", "Lena", "Mateo", "Nina", "Omar", "Priya",
    "Quinn", "Rosa", "Sven", "Tara", "Uma", "Viktor", "Wei", "Yara", "Zane",
]
_LAST_NAMES = [
    "Anderson", "Brown", "Cruz", "Diaz", "Evans", "Fischer", "Garcia",
    "Hassan", "Ito", "Johnson", "Khan", "Lopez", "Mehta", "Nguyen", "Owens",
    "Patel", "Rossi", "Singh", "Tanaka", "Wang",
]


def _sample_numeric(spec: ColumnSpec, rng: np.random.Generator, n: int) -> np.ndarray:
    dist = spec.distribution
    if dist == "uniform":
        values = rng.uniform(spec.min, spec.max, size=n)
    elif dist == "normal":
        mean = spec.mean if spec.mean is not None else 0.0
        std = spec.std if spec.std is not None else 1.0
        values = rng.normal(mean, std, size=n)
        if spec.min is not None or spec.max is not None:
            lo = spec.min if spec.min is not None else -np.inf
            hi = spec.max if spec.max is not None else np.inf
            values = np.clip(values, lo, hi)
    elif dist == "lognormal":
        mean = spec.mean if spec.mean is not None else 0.0
        std = spec.std if spec.std is not None else 1.0
        values = rng.lognormal(mean, std, size=n)
    elif dist == "exponential":
        scale = spec.mean if spec.mean is not None else 1.0
        values = rng.exponential(scale, size=n)
    else:
        raise ValueError(
            f"Column '{spec.name}': unknown distribution '{dist}'."
        )
    return values.astype(float)


def _generate_base(spec: ColumnSpec, rng: np.random.Generator, n: int) -> np.ndarray:
    """Generate values before outlier/null injection."""
    dtype = spec.dtype

    if dtype in {"int", "float"}:
        values = _sample_numeric(spec, rng, n)
        if dtype == "int":
            return np.rint(values).astype("int64").astype(object)
        return np.round(values, spec.decimals).astype(object)

    if dtype == "category":
        probs = None
        if spec.weights is not None:
            total = float(sum(spec.weights))
            probs = [w / total for w in spec.weights]
        idx = rng.choice(len(spec.categories), size=n, p=probs)
        cats = np.array(spec.categories, dtype=object)
        return cats[idx]

    if dtype == "bool":
        return rng.random(n) < spec.p_true

    if dtype == "datetime":
        start = pd.Timestamp(spec.min if spec.min is not None else "2020-01-01")
        end = pd.Timestamp(spec.max if spec.max is not None else "2025-01-01")
        span = (end - start).value  # nanoseconds
        offsets = rng.integers(0, max(span, 1), size=n)
        stamps = pd.to_datetime(start.value + offsets)
        if spec.datetime_format:
            return np.array(
                [t.strftime(spec.datetime_format) for t in stamps], dtype=object
            )
        return np.array(stamps, dtype=object)

    if dtype == "text":
        return random_sentences(rng, n, spec.text_words)

    if dtype == "uuid":
        # 128-bit ints exceed int64, so draw raw bytes from the seeded RNG.
        return np.array(
            [str(_uuid.UUID(int=int.from_bytes(rng.bytes(16), "big"))) for _ in range(n)],
            dtype=object,
        )

    if dtype == "name":
        first = rng.choice(_FIRST_NAMES, size=n)
        last = rng.choice(_LAST_NAMES, size=n)
        return np.array([f"{f} {l}" for f, l in zip(first, last)], dtype=object)

    if dtype == "email":
        first = rng.choice(_FIRST_NAMES, size=n)
        last = rng.choice(_LAST_NAMES, size=n)
        nums = rng.integers(1, 999, size=n)
        domains = rng.choice(["example.com", "mail.com", "test.org", "demo.io"], size=n)
        return np.array(
            [f"{f.lower()}.{l.lower()}{num}@{d}" for f, l, num, d in zip(first, last, nums, domains)],
            dtype=object,
        )

    raise ValueError(f"Column '{spec.name}': unsupported dtype '{dtype}'.")


def _inject_nulls(values: np.ndarray, spec: ColumnSpec, rng: np.random.Generator) -> np.ndarray:
    if spec.null_pct <= 0:
        return values
    n = len(values)
    k = int(round(n * spec.null_pct))
    if k <= 0:
        return values
    idx = rng.choice(n, size=k, replace=False)
    values = values.astype(object)
    values[idx] = None
    return values


def generate_column(spec: ColumnSpec, rng: np.random.Generator, n: int) -> np.ndarray:
    """Generate ``n`` values for ``spec`` including outliers and nulls."""
    values = _generate_base(spec, rng, n)
    if spec.outlier_pct > 0:
        values = inject_outliers(values, spec, rng)
    values = _inject_nulls(values, spec, rng)
    return values
