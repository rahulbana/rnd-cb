"""Outlier injection.

Replaces a user-controlled fraction of a column's values with anomalous ones.
The strategy depends on the column type:

* Numeric columns get values pushed several standard deviations / range-widths
  beyond the normal data, alternating high and low.
* Category columns get a sentinel ``__OUTLIER__`` value that is, by
  construction, never part of the configured categories.
* Other types fall back to the category-style sentinel.
"""

from __future__ import annotations

import numpy as np

OUTLIER_LABEL = "__OUTLIER__"


def _outlier_indices(n: int, pct: float, rng: np.random.Generator) -> np.ndarray:
    k = int(round(n * pct))
    if k <= 0:
        return np.empty(0, dtype=int)
    k = min(k, n)
    return rng.choice(n, size=k, replace=False)


def inject_outliers(values: np.ndarray, spec, rng: np.random.Generator) -> np.ndarray:
    """Return ``values`` with ``spec.outlier_pct`` of entries replaced.

    The number of outliers is ``round(n * outlier_pct)`` so the realized
    fraction matches the request as closely as integer counts allow.
    """
    n = len(values)
    idx = _outlier_indices(n, spec.outlier_pct, rng)
    if idx.size == 0:
        return values

    values = values.astype(object)

    if spec.dtype in {"int", "float"}:
        numeric = np.array(
            [v for v in values if isinstance(v, (int, float)) and v is not None],
            dtype=float,
        )
        if numeric.size == 0:
            return values
        center = float(np.median(numeric))
        spread = float(np.std(numeric)) or (abs(center) or 1.0)
        # Push outliers 4-8 spreads away, alternating direction.
        magnitudes = rng.uniform(4.0, 8.0, size=idx.size)
        signs = rng.choice([-1.0, 1.0], size=idx.size)
        outliers = center + signs * magnitudes * spread
        if spec.dtype == "int":
            outliers = np.rint(outliers).astype("int64")
            for i, o in zip(idx, outliers):
                values[i] = int(o)
        else:
            outliers = np.round(outliers, spec.decimals)
            for i, o in zip(idx, outliers):
                values[i] = float(o)
        return values

    # Non-numeric: drop in an out-of-vocabulary sentinel.
    for i in idx:
        values[i] = OUTLIER_LABEL
    return values
