"""The autonomous profiling engine.

Given a raw CSV, this module looks at the data from several independent
perspectives — structural, type-based, statistical, distributional,
relational and quality — and produces a structured profile. The LLM agent
later turns that structured profile into natural-language inferences, but
everything here is deterministic and works without any API key.
"""

from __future__ import annotations

import io
import math
import re
from typing import Any

import numpy as np
import pandas as pd

from .models import (
    ChartSpec,
    ColumnProfile,
    Correlation,
    DatasetOverview,
)

# Values that frequently mean "missing" but slip through as plain strings.
_NA_TOKENS = ["", "na", "n/a", "nan", "null", "none", "-", "--", "?"]
_TRUE_TOKENS = {"true", "yes", "y", "1", "t"}
_FALSE_TOKENS = {"false", "no", "n", "0", "f"}


def read_csv(raw: bytes, filename: str) -> pd.DataFrame:
    """Robustly parse CSV bytes into a DataFrame.

    Tries a couple of separators/encodings before giving up so that the
    agent copes with the messy real-world files users actually upload.
    """
    last_err: Exception | None = None
    for encoding in ("utf-8", "latin-1"):
        for sep in (",", ";", "\t", "|"):
            try:
                df = pd.read_csv(
                    io.BytesIO(raw),
                    sep=sep,
                    encoding=encoding,
                    na_values=_NA_TOKENS,
                    keep_default_na=True,
                    skipinitialspace=True,
                )
                # A successful parse should yield more than one column unless
                # the file genuinely has one column.
                if df.shape[1] >= 1 and df.shape[0] >= 1:
                    return _coerce_types(df)
            except Exception as exc:  # noqa: BLE001 - we deliberately try fallbacks
                last_err = exc
    raise ValueError(f"Could not parse '{filename}' as CSV: {last_err}")


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Attempt smarter typing than pandas' defaults.

    Object columns that are really numbers, booleans or dates get upgraded so
    the downstream perspectives treat them correctly.
    """
    for col in df.columns:
        series = df[col]
        if series.dtype != object:
            continue

        non_null = series.dropna().astype(str).str.strip()
        if non_null.empty:
            continue

        lowered = non_null.str.lower()

        # Boolean detection.
        if set(lowered.unique()).issubset(_TRUE_TOKENS | _FALSE_TOKENS):
            df[col] = lowered.map(lambda v: v in _TRUE_TOKENS).reindex(series.index)
            continue

        # Numeric detection (strip thousands separators & currency symbols).
        cleaned = non_null.str.replace(r"[,$%\s]", "", regex=True)
        numeric = pd.to_numeric(cleaned, errors="coerce")
        if numeric.notna().mean() >= 0.9:
            df[col] = pd.to_numeric(
                series.astype(str).str.replace(r"[,$%\s]", "", regex=True),
                errors="coerce",
            )
            continue

        # Datetime detection.
        looks_datey = lowered.str.contains(r"\d{1,4}[-/]\d{1,2}[-/]\d{1,4}|\d{4}").mean()
        if looks_datey >= 0.7:
            parsed = pd.to_datetime(series, errors="coerce")
            if parsed.notna().mean() >= 0.8:
                df[col] = parsed
    return df


def _infer_semantic_type(series: pd.Series, name: str, n_rows: int) -> str:
    """Classify a column the way a human analyst would read it."""
    non_null = series.dropna()
    if non_null.empty:
        return "empty"

    nunique = non_null.nunique()
    if nunique == 1:
        return "constant"

    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    if pd.api.types.is_numeric_dtype(series):
        # Looks like an ID if (almost) every value is unique and integral.
        is_int = (non_null % 1 == 0).all()
        looks_like_id = (
            is_int
            and nunique >= 0.95 * len(non_null)
            and re.search(r"(^id$|_id$|^id_|key$|code$|uuid|guid)", name, re.IGNORECASE)
        )
        if looks_like_id:
            return "identifier"
        # Small set of integers -> categorical encoding (e.g. 0/1/2 classes).
        if is_int and nunique <= max(10, 0.05 * n_rows):
            return "categorical" if nunique <= 10 else "integer"
        return "integer" if is_int else "float"

    # Object / string.
    nunique_ratio = nunique / len(non_null)
    avg_len = non_null.astype(str).str.len().mean()
    if nunique_ratio >= 0.9 and avg_len > 12:
        return "identifier" if re.search(r"id|uuid|guid|key", name, re.IGNORECASE) else "text"
    if avg_len > 40:
        return "text"
    return "categorical"


def _safe_float(value: Any) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _profile_column(series: pd.Series, name: str, n_rows: int) -> ColumnProfile:
    semantic = _infer_semantic_type(series, name, n_rows)
    non_null = series.dropna()
    missing = int(series.isna().sum())
    unique = int(non_null.nunique())

    profile = ColumnProfile(
        name=name,
        dtype=str(series.dtype),
        semantic_type=semantic,  # type: ignore[arg-type]
        count=int(non_null.shape[0]),
        missing=missing,
        missing_pct=round(missing / n_rows * 100, 2) if n_rows else 0.0,
        unique=unique,
        unique_pct=round(unique / n_rows * 100, 2) if n_rows else 0.0,
    )
    notes: list[str] = []

    # --- Numeric perspective -------------------------------------------------
    if semantic in {"integer", "float"} and not non_null.empty:
        values = non_null.astype(float)
        profile.mean = _safe_float(values.mean())
        profile.std = _safe_float(values.std())
        profile.min = _safe_float(values.min())
        profile.max = _safe_float(values.max())
        profile.median = _safe_float(values.median())
        profile.q1 = _safe_float(values.quantile(0.25))
        profile.q3 = _safe_float(values.quantile(0.75))
        profile.skew = _safe_float(values.skew())
        profile.kurtosis = _safe_float(values.kurtosis())
        profile.zeros = int((values == 0).sum())
        profile.negatives = int((values < 0).sum())

        # IQR-based outlier detection.
        if profile.q1 is not None and profile.q3 is not None:
            iqr = profile.q3 - profile.q1
            low, high = profile.q1 - 1.5 * iqr, profile.q3 + 1.5 * iqr
            profile.outlier_count = int(((values < low) | (values > high)).sum())

        # Histogram for the distribution chart.
        counts, edges = np.histogram(values, bins=min(20, max(5, unique)))
        profile.histogram = {
            "counts": [float(c) for c in counts],
            "edges": [float(e) for e in edges],
        }

        if profile.skew is not None and abs(profile.skew) > 1:
            notes.append(
                f"Strongly {'right' if profile.skew > 0 else 'left'}-skewed "
                f"(skew={profile.skew:.2f}) — median is a better summary than the mean."
            )
        if profile.outlier_count:
            notes.append(f"{profile.outlier_count} potential outlier(s) by the 1.5×IQR rule.")

    # --- Boolean perspective -------------------------------------------------
    elif semantic == "boolean":
        as_bool = non_null.astype(bool)
        profile.true_count = int(as_bool.sum())
        profile.false_count = int((~as_bool).sum())
        ratio = profile.true_count / max(1, profile.true_count + profile.false_count)
        notes.append(f"{ratio * 100:.1f}% true / {(1 - ratio) * 100:.1f}% false.")

    # --- Datetime perspective ------------------------------------------------
    elif semantic == "datetime":
        profile.min_date = str(non_null.min())
        profile.max_date = str(non_null.max())
        span = pd.to_datetime(non_null.max()) - pd.to_datetime(non_null.min())
        notes.append(f"Spans {span.days} day(s).")

    # --- Categorical / text / identifier perspective ------------------------
    if semantic in {"categorical", "boolean", "text", "constant", "identifier"}:
        vc = non_null.astype(str).value_counts().head(8)
        profile.top_values = [
            {"value": str(idx), "count": int(cnt), "pct": round(cnt / n_rows * 100, 2)}
            for idx, cnt in vc.items()
        ]
        if semantic in {"text", "categorical"}:
            profile.avg_length = _safe_float(non_null.astype(str).str.len().mean())

    # --- Quality notes -------------------------------------------------------
    if profile.missing_pct > 50:
        notes.append(f"Over half the values are missing ({profile.missing_pct:.1f}%).")
    elif profile.missing_pct > 0:
        notes.append(f"{profile.missing_pct:.1f}% missing values.")
    if semantic == "constant":
        notes.append("Single constant value — carries no information for modelling.")
    if semantic == "identifier":
        notes.append("Looks like a unique identifier — usually excluded from statistics.")

    profile.notes = notes
    return profile


def _compute_correlations(df: pd.DataFrame, columns: list[ColumnProfile]) -> list[Correlation]:
    numeric_names = [c.name for c in columns if c.semantic_type in {"integer", "float"}]
    if len(numeric_names) < 2:
        return []

    corr = df[numeric_names].corr(numeric_only=True)
    results: list[Correlation] = []
    seen: set[frozenset[str]] = set()
    for a in numeric_names:
        for b in numeric_names:
            if a == b:
                continue
            key = frozenset((a, b))
            if key in seen:
                continue
            seen.add(key)
            coef = corr.loc[a, b]
            if pd.isna(coef):
                continue
            coef = float(coef)
            magnitude = abs(coef)
            if magnitude >= 0.7:
                strength = "strong"
            elif magnitude >= 0.4:
                strength = "moderate"
            elif magnitude >= 0.2:
                strength = "weak"
            else:
                continue  # ignore negligible relationships
            results.append(
                Correlation(
                    column_a=a,
                    column_b=b,
                    coefficient=round(coef, 3),
                    strength=strength,
                    direction="positive" if coef > 0 else "negative",
                )
            )
    results.sort(key=lambda c: abs(c.coefficient), reverse=True)
    return results[:15]


def _build_charts(
    df: pd.DataFrame, columns: list[ColumnProfile], correlations: list[Correlation]
) -> list[ChartSpec]:
    """Pick the most informative charts automatically."""
    charts: list[ChartSpec] = []
    by_name = {c.name: c for c in columns}

    # 1. Column-type composition (always useful).
    type_counts: dict[str, int] = {}
    for c in columns:
        type_counts[c.semantic_type] = type_counts.get(c.semantic_type, 0) + 1
    charts.append(
        ChartSpec(
            id="type-composition",
            type="pie",
            title="Column type composition",
            description="How the agent classified each column by semantic type.",
            x_key="name",
            y_keys=["value"],
            data=[{"name": k, "value": v} for k, v in sorted(type_counts.items())],
        )
    )

    # 2. Missing-data overview (only columns that actually have gaps).
    missing = [
        {"column": c.name, "missing_pct": c.missing_pct}
        for c in columns
        if c.missing_pct > 0
    ]
    if missing:
        missing.sort(key=lambda d: d["missing_pct"], reverse=True)
        charts.append(
            ChartSpec(
                id="missing-data",
                type="bar",
                title="Missing data by column",
                description="Percentage of missing values per column — your data-quality map.",
                x_key="column",
                y_keys=["missing_pct"],
                data=missing[:20],
            )
        )

    # 3. Distribution histograms for up to 3 numeric columns.
    numeric = [c for c in columns if c.semantic_type in {"integer", "float"} and c.histogram]
    numeric.sort(key=lambda c: (c.std or 0), reverse=True)
    for col in numeric[:3]:
        hist = col.histogram or {}
        edges = hist.get("edges", [])
        counts = hist.get("counts", [])
        data = [
            {
                "bin": f"{edges[i]:.1f}–{edges[i + 1]:.1f}",
                "count": counts[i],
            }
            for i in range(len(counts))
        ]
        charts.append(
            ChartSpec(
                id=f"hist-{col.name}",
                type="histogram",
                title=f"Distribution of {col.name}",
                description=(
                    f"Spread of values for {col.name} "
                    f"(mean {col.mean:.2f}, median {col.median:.2f})."
                    if col.mean is not None and col.median is not None
                    else f"Spread of values for {col.name}."
                ),
                x_key="bin",
                y_keys=["count"],
                data=data,
            )
        )

    # 4. Category breakdown for the most informative categorical column.
    categoricals = [
        c
        for c in columns
        if c.semantic_type in {"categorical", "boolean"} and 1 < c.unique <= 15 and c.top_values
    ]
    categoricals.sort(key=lambda c: c.unique)
    for col in categoricals[:2]:
        charts.append(
            ChartSpec(
                id=f"cat-{col.name}",
                type="bar",
                title=f"Breakdown of {col.name}",
                description=f"Frequency of each category in {col.name}.",
                x_key="value",
                y_keys=["count"],
                data=[{"value": tv["value"], "count": tv["count"]} for tv in col.top_values],
            )
        )

    # 5. Scatter for the strongest correlated numeric pair.
    if correlations:
        top = correlations[0]
        if top.column_a in by_name and top.column_b in by_name:
            sample = df[[top.column_a, top.column_b]].dropna()
            if len(sample) > 500:
                sample = sample.sample(500, random_state=42)
            charts.append(
                ChartSpec(
                    id="scatter-top-corr",
                    type="scatter",
                    title=f"{top.column_a} vs {top.column_b}",
                    description=(
                        f"Strongest relationship found: {top.strength} {top.direction} "
                        f"correlation (r={top.coefficient})."
                    ),
                    x_key=top.column_a,
                    y_keys=[top.column_b],
                    data=[
                        {top.column_a: _safe_float(r[top.column_a]), top.column_b: _safe_float(r[top.column_b])}
                        for _, r in sample.iterrows()
                    ],
                )
            )

    # 6. Correlation heatmap data (numeric matrix).
    numeric_names = [c.name for c in columns if c.semantic_type in {"integer", "float"}]
    if len(numeric_names) >= 2:
        corr = df[numeric_names].corr(numeric_only=True).round(2)
        heat = [
            {"x": a, "y": b, "value": _safe_float(corr.loc[a, b])}
            for a in numeric_names
            for b in numeric_names
        ]
        charts.append(
            ChartSpec(
                id="corr-heatmap",
                type="heatmap",
                title="Correlation heatmap",
                description="Pairwise Pearson correlation across all numeric columns.",
                data=heat,
                meta={"labels": numeric_names},
            )
        )

    return charts


def profile_dataframe(df: pd.DataFrame, filename: str) -> dict[str, Any]:
    """Run every perspective and return the structured analysis dictionary."""
    n_rows = int(df.shape[0])
    columns = [_profile_column(df[col], str(col), n_rows) for col in df.columns]
    correlations = _compute_correlations(df, columns)
    charts = _build_charts(df, columns, correlations)

    total_cells = int(df.shape[0] * df.shape[1])
    missing_cells = int(df.isna().sum().sum())
    type_breakdown: dict[str, int] = {}
    for c in columns:
        type_breakdown[c.semantic_type] = type_breakdown.get(c.semantic_type, 0) + 1

    overview = DatasetOverview(
        filename=filename,
        rows=n_rows,
        columns=int(df.shape[1]),
        total_cells=total_cells,
        missing_cells=missing_cells,
        missing_pct=round(missing_cells / total_cells * 100, 2) if total_cells else 0.0,
        duplicate_rows=int(df.duplicated().sum()),
        memory_kb=round(df.memory_usage(deep=True).sum() / 1024, 1),
        type_breakdown=type_breakdown,
    )

    # JSON-safe sample rows for the LLM and the preview table.
    sample = df.head(20).replace({np.nan: None})
    sample_rows = sample.astype(object).where(pd.notna(sample), None).to_dict(orient="records")

    return {
        "overview": overview,
        "columns": columns,
        "correlations": correlations,
        "charts": charts,
        "sample_rows": sample_rows,
    }
