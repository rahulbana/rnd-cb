"""Run the design document's example prompts end to end.

    python examples/generate_examples.py

Writes datasets + reports under ``datasets/`` and prints a one-line summary per
prompt (task, rows, ML-readiness score).
"""

from __future__ import annotations

from app.services.generator import DatasetService

PROMPTS = [
    "Generate a telecom churn dataset with 25000 customers and 12% churn.",
    "Create a regression dataset for predicting house prices using 20 features.",
    "Build a loan default dataset with demographics and 9% default rate.",
    "Generate a manufacturing sensor time-series dataset with injected anomalies.",
    "Create a customer segmentation dataset with 8000 rows for clustering.",
    "Create a fraud detection dataset with 20000 records and 2% fraud rate.",
]


def main() -> None:
    service = DatasetService()
    for prompt in PROMPTS:
        result = service.generate_from_prompt(prompt, formats=["csv"])
        e = result.evaluation
        score = e.ml_readiness_score if e else "n/a"
        metrics = e.metrics if e else {}
        print(
            f"[{result.spec.task_type.value:26s}] "
            f"rows={len(result.data):>7,} score={score!s:>5} "
            f"metrics={metrics}  <- {prompt}"
        )


if __name__ == "__main__":
    main()
