"""Seeded random-number helpers so every run is reproducible."""

from __future__ import annotations

import numpy as np


def make_rng(seed: int) -> np.random.Generator:
    """Return a NumPy ``Generator`` seeded deterministically."""

    return np.random.default_rng(seed)


def sample_distribution(
    rng: np.random.Generator,
    distribution: str,
    size: int,
    params: dict[str, float] | None = None,
) -> np.ndarray:
    """Draw ``size`` samples from a named distribution.

    Unknown distributions fall back to a standard normal so generation never
    hard-fails on an unexpected planner output.
    """

    p = params or {}
    if distribution == "normal":
        return rng.normal(p.get("mean", 0.0), p.get("std", 1.0), size)
    if distribution == "uniform":
        return rng.uniform(p.get("low", 0.0), p.get("high", 1.0), size)
    if distribution == "poisson":
        return rng.poisson(p.get("lam", 3.0), size).astype(float)
    if distribution == "gamma":
        return rng.gamma(p.get("shape", 2.0), p.get("scale", 1.0), size)
    if distribution == "exponential":
        return rng.exponential(p.get("scale", 1.0), size)
    if distribution == "lognormal":
        return rng.lognormal(p.get("mean", 0.0), p.get("sigma", 1.0), size)
    if distribution == "beta":
        return rng.beta(p.get("a", 2.0), p.get("b", 2.0), size)
    if distribution == "powerlaw":
        return rng.power(p.get("a", 2.0), size)
    return rng.normal(0.0, 1.0, size)
