"""The reasoning layer.

Takes the deterministic profile produced by ``analysis.py`` and asks an
OpenAI model to act as a senior data analyst: read the dataset from multiple
perspectives, state what it understands the data to be, and surface concrete
inferences and follow-up questions.

If no OpenAI key is configured the module still returns a useful, rule-based
narrative so the product is fully functional offline.
"""

from __future__ import annotations

import json
from typing import Any

from .config import settings
from .models import ColumnProfile, Correlation, DatasetOverview

SYSTEM_PROMPT = """You are an autonomous data-analysis agent. You receive a \
structured statistical profile of a CSV that a deterministic engine already \
computed (per-column types, distributions, missingness, correlations). Your job \
is to interpret it like a thoughtful senior data analyst.

Analyse the dataset from multiple perspectives:
- What this dataset most likely represents (its domain and the grain of a row).
- The role of each important column (measure, dimension, identifier, target).
- Data-quality risks (missingness, outliers, constants, duplicates).
- Relationships and patterns worth investigating.

Respond with STRICT JSON only, matching this schema:
{
  "narrative": "3-5 sentence plain-English summary of what the data is and what stands out",
  "inferences": ["concise, specific, evidence-backed inference", ...],  // 5-8 items
  "suggested_questions": ["analytical question a user could explore next", ...]  // 3-5 items
}
Be concrete and reference real column names and numbers. Do not invent columns."""


def _build_compact_profile(
    overview: DatasetOverview,
    columns: list[ColumnProfile],
    correlations: list[Correlation],
    sample_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Trim the profile to a compact, token-friendly shape for the model."""
    compact_cols = []
    for c in columns:
        entry: dict[str, Any] = {
            "name": c.name,
            "type": c.semantic_type,
            "missing_pct": c.missing_pct,
            "unique": c.unique,
        }
        if c.mean is not None:
            entry.update(
                {"mean": c.mean, "min": c.min, "max": c.max, "median": c.median, "skew": c.skew}
            )
        if c.outlier_count:
            entry["outliers"] = c.outlier_count
        if c.true_count is not None:
            entry["true"] = c.true_count
            entry["false"] = c.false_count
        if c.top_values:
            entry["top_values"] = c.top_values[:5]
        compact_cols.append(entry)

    return {
        "overview": overview.model_dump(),
        "columns": compact_cols,
        "correlations": [c.model_dump() for c in correlations[:10]],
        "sample_rows": sample_rows[: settings.max_rows_for_llm],
    }


def _fallback_narrative(
    overview: DatasetOverview,
    columns: list[ColumnProfile],
    correlations: list[Correlation],
) -> dict[str, Any]:
    """Deterministic, no-API analysis so the app works without a key."""
    numeric = [c for c in columns if c.semantic_type in {"integer", "float"}]
    categorical = [c for c in columns if c.semantic_type == "categorical"]
    booleans = [c for c in columns if c.semantic_type == "boolean"]
    dates = [c for c in columns if c.semantic_type == "datetime"]
    ids = [c for c in columns if c.semantic_type == "identifier"]

    narrative = (
        f"The dataset '{overview.filename}' has {overview.rows:,} rows and "
        f"{overview.columns} columns ({len(numeric)} numeric, {len(categorical)} categorical, "
        f"{len(booleans)} boolean, {len(dates)} datetime). "
    )
    if overview.missing_pct:
        narrative += f"About {overview.missing_pct:.1f}% of all cells are missing. "
    if overview.duplicate_rows:
        narrative += f"There are {overview.duplicate_rows} duplicate row(s). "
    if dates:
        narrative += f"It carries a time dimension via '{dates[0].name}', suggesting trend analysis is possible. "
    narrative += "Below are the strongest signals the profiling engine found."

    inferences: list[str] = []
    for c in sorted(columns, key=lambda x: x.missing_pct, reverse=True):
        if c.missing_pct > 20:
            inferences.append(
                f"Column '{c.name}' is {c.missing_pct:.1f}% empty — consider imputation or dropping it."
            )
    for c in numeric:
        if c.skew is not None and abs(c.skew) > 1.5:
            inferences.append(
                f"'{c.name}' is heavily skewed (skew={c.skew:.2f}); a log transform may help modelling."
            )
        if c.outlier_count and c.count and c.outlier_count / c.count > 0.05:
            inferences.append(
                f"'{c.name}' has {c.outlier_count} outliers (~{c.outlier_count / c.count * 100:.0f}% of values)."
            )
    for corr in correlations[:3]:
        inferences.append(
            f"'{corr.column_a}' and '{corr.column_b}' show a {corr.strength} {corr.direction} "
            f"relationship (r={corr.coefficient})."
        )
    for c in booleans:
        if c.true_count is not None and c.false_count is not None:
            total = c.true_count + c.false_count
            ratio = c.true_count / total if total else 0
            if ratio < 0.1 or ratio > 0.9:
                inferences.append(
                    f"Boolean '{c.name}' is imbalanced ({ratio * 100:.0f}% true) — watch for class imbalance."
                )
    if ids:
        inferences.append(
            f"'{ids[0].name}' looks like a row identifier and should be excluded from statistics."
        )
    if not inferences:
        inferences.append("No major data-quality issues detected — the dataset looks clean and ready to use.")

    questions: list[str] = []
    if dates and numeric:
        questions.append(f"How does '{numeric[0].name}' trend over '{dates[0].name}'?")
    if correlations:
        questions.append(
            f"Is the link between '{correlations[0].column_a}' and "
            f"'{correlations[0].column_b}' causal or coincidental?"
        )
    if categorical and numeric:
        questions.append(
            f"Does '{numeric[0].name}' differ across categories of '{categorical[0].name}'?"
        )
    questions.append("Which column would make the best prediction target, and what drives it?")

    return {
        "narrative": narrative,
        "inferences": inferences[:8],
        "suggested_questions": questions[:5],
    }


def generate_insights(
    overview: DatasetOverview,
    columns: list[ColumnProfile],
    correlations: list[Correlation],
    sample_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    """Return (insights, llm_used)."""
    if not settings.llm_enabled:
        return _fallback_narrative(overview, columns, correlations), False

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        compact = _build_compact_profile(overview, columns, correlations, sample_rows)
        completion = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": "Here is the structured profile of the dataset:\n\n"
                    + json.dumps(compact, default=str),
                },
            ],
        )
        payload = json.loads(completion.choices[0].message.content or "{}")
        # Guard against a malformed response.
        insights = {
            "narrative": payload.get("narrative") or "",
            "inferences": payload.get("inferences") or [],
            "suggested_questions": payload.get("suggested_questions") or [],
        }
        if not insights["narrative"] or not insights["inferences"]:
            raise ValueError("LLM returned an incomplete payload")
        return insights, True
    except Exception:  # noqa: BLE001 - never let the LLM break the request
        # Fall back gracefully but mark that the LLM was not used.
        return _fallback_narrative(overview, columns, correlations), False
