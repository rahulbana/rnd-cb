"""Planner agent: natural language -> :class:`DatasetSpec`.

Two backends implement the same ``plan(prompt) -> DatasetSpec`` interface:

* :class:`HeuristicPlanner` (default) parses the prompt with keyword/regex rules
  and the domain scenario library. It requires no network or API key, so the
  whole platform is runnable and testable offline.
* :class:`LLMPlanner` is a thin, optional wrapper that asks an LLM to emit the
  spec as JSON. It is only imported/used when ``PLANNER_BACKEND=llm``.

Keeping the contract identical means the rest of the pipeline never knows or
cares which planner produced the spec.
"""

from __future__ import annotations

import re

from app.agents.base import Agent
from app.config import settings
from app.models.spec import (
    DatasetSpec,
    Distribution,
    DType,
    FeatureRole,
    FeatureSpec,
    QualitySpec,
    TargetSpec,
    TaskType,
)
from app.prompts.scenarios import SCENARIOS, match_scenario
from app.utils.text import (
    parse_feature_counts,
    parse_int_count,
    parse_percentage,
    slugify,
)

# Keyword groups used when no scenario template matches.
_TASK_KEYWORDS: list[tuple[TaskType, list[str]]] = [
    (TaskType.TIME_SERIES,
     ["time series", "time-series", "forecast", "sensor", "iot", "temperature",
      "traffic", "energy consumption", "stock price"]),
    (TaskType.CLUSTERING,
     ["cluster", "segment", "segmentation", "grouping", "unsupervised"]),
    (TaskType.MULTICLASS_CLASSIFICATION,
     ["multi-class", "multiclass", "categories", "classify into"]),
    (TaskType.REGRESSION,
     ["regression", "predict price", "predict the price", "predict sales",
      "predict salary", "predict amount", "estimate", "forecast value"]),
    (TaskType.BINARY_CLASSIFICATION,
     ["classification", "detect", "predict whether", "fraud", "churn", "spam",
      "default", "attrition", "disease"]),
]


class HeuristicPlanner(Agent):
    """Deterministic, offline planner."""

    name = "planner"

    def run(self, prompt: str) -> DatasetSpec:
        return self.plan(prompt)

    def plan(self, prompt: str) -> DatasetSpec:
        scenario_key = match_scenario(prompt)
        if scenario_key:
            spec = self._from_scenario(scenario_key, prompt)
        else:
            spec = self._from_scratch(prompt)

        self._apply_common_overrides(spec, prompt)
        self.log(
            f"planned task={spec.task_type.value} rows={spec.n_rows} "
            f"features={len(spec.features)} domain={spec.domain}"
        )
        return spec

    # -- scenario-based planning ------------------------------------------
    def _from_scenario(self, key: str, prompt: str) -> DatasetSpec:
        cfg = SCENARIOS[key]
        # Deep-copy feature specs so scenario templates are never mutated.
        features = [f.model_copy(deep=True) for f in cfg["features"]]
        task_type: TaskType = cfg["task_type"]

        target = None
        if task_type.is_classification:
            positive_rate = (
                parse_percentage(prompt, cfg["keywords"] + ["rate", "positive"])
                or cfg.get("positive_rate", 0.5)
            )
            target = TargetSpec(
                name=cfg["target_name"],
                positive_rate=positive_rate,
                n_classes=2,
            )
        elif task_type.is_regression:
            target = TargetSpec(name=cfg["target_name"], nonlinear=False)
        elif task_type == TaskType.CLUSTERING:
            target = TargetSpec(name=cfg["target_name"], n_classes=4)

        spec = DatasetSpec(
            name=slugify(f"{key}_dataset"),
            description=prompt.strip(),
            domain=cfg["domain"],
            task_type=task_type,
            n_rows=1000,
            features=features,
            target=target,
            metadata={"scenario": key, "prompt": prompt},
        )
        return spec

    # -- generic planning --------------------------------------------------
    def _from_scratch(self, prompt: str) -> DatasetSpec:
        task_type = self._infer_task(prompt)
        n_numeric, n_categorical = parse_feature_counts(prompt)
        n_numeric = n_numeric if n_numeric is not None else 8
        n_categorical = n_categorical if n_categorical is not None else 3

        features = self._synthetic_features(n_numeric, n_categorical)

        target = None
        if task_type.is_classification:
            n_classes = 2
            if task_type == TaskType.MULTICLASS_CLASSIFICATION:
                m = re.search(r"(\d+)\s*class", prompt.lower())
                n_classes = int(m.group(1)) if m else 3
            positive_rate = parse_percentage(prompt, ["positive", "rate", "event"]) or 0.5
            target = TargetSpec(
                name="target", positive_rate=positive_rate, n_classes=n_classes
            )
        elif task_type.is_regression:
            target = TargetSpec(name="target")
        elif task_type == TaskType.CLUSTERING:
            target = TargetSpec(name="cluster", n_classes=4)
        elif task_type == TaskType.TIME_SERIES:
            target = TargetSpec(name="value")

        return DatasetSpec(
            name=slugify(self._infer_name(prompt)),
            description=prompt.strip(),
            domain="generic",
            task_type=task_type,
            n_rows=1000,
            features=features,
            target=target,
            metadata={"scenario": None, "prompt": prompt},
        )

    def _infer_task(self, prompt: str) -> TaskType:
        lowered = prompt.lower()
        for task_type, keywords in _TASK_KEYWORDS:
            if any(kw in lowered for kw in keywords):
                return task_type
        return TaskType.BINARY_CLASSIFICATION

    def _infer_name(self, prompt: str) -> str:
        # Use the first few informative words of the prompt.
        words = re.findall(r"[a-zA-Z]+", prompt)
        stop = {"generate", "create", "build", "a", "an", "the", "dataset",
                "with", "for", "of", "and", "to"}
        keep = [w for w in words if w.lower() not in stop][:3]
        return "_".join(keep) if keep else "dataset"

    def _synthetic_features(
        self, n_numeric: int, n_categorical: int
    ) -> list[FeatureSpec]:
        features: list[FeatureSpec] = []
        distributions = [
            Distribution.NORMAL,
            Distribution.GAMMA,
            Distribution.EXPONENTIAL,
            Distribution.LOGNORMAL,
            Distribution.UNIFORM,
        ]
        for i in range(max(0, n_numeric)):
            dist = distributions[i % len(distributions)]
            features.append(
                FeatureSpec(
                    name=f"num_feature_{i + 1}",
                    dtype=DType.FLOAT,
                    distribution=dist,
                    description=f"Synthetic numeric feature #{i + 1}",
                )
            )
        for i in range(max(0, n_categorical)):
            k = 3 + (i % 4)
            features.append(
                FeatureSpec(
                    name=f"cat_feature_{i + 1}",
                    dtype=DType.CATEGORY,
                    categories=[f"cat_{chr(97 + j)}" for j in range(k)],
                    description=f"Synthetic categorical feature #{i + 1}",
                )
            )
        return features

    # -- overrides shared by both planning paths --------------------------
    def _apply_common_overrides(self, spec: DatasetSpec, prompt: str) -> None:
        rows = parse_int_count(prompt)
        if rows:
            spec.n_rows = max(1, min(rows, settings.max_rows))

        # Data-quality signals.
        quality = QualitySpec()
        if any(w in prompt.lower() for w in ["missing", "nan", "null", "incomplete"]):
            quality.missing_rate = 0.05
        if "duplicate" in prompt.lower():
            quality.duplicate_rate = 0.02
        if any(w in prompt.lower() for w in ["outlier", "anomaly", "anomalies"]):
            quality.outlier_rate = 0.02
        if "noise" in prompt.lower() or "noisy" in prompt.lower():
            quality.noise = 0.1
        if any(w in prompt.lower() for w in ["dirty", "messy", "realistic quality"]):
            quality.missing_rate = max(quality.missing_rate, 0.05)
            quality.outlier_rate = max(quality.outlier_rate, 0.02)
            quality.duplicate_rate = max(quality.duplicate_rate, 0.01)
        spec.quality = quality

        # Adjust generic numeric feature count if the prompt asked for a count
        # even though a scenario matched.
        n_numeric, n_categorical = parse_feature_counts(prompt)
        if spec.metadata.get("scenario") and (n_numeric or n_categorical):
            self._pad_scenario_features(spec, n_numeric, n_categorical)

    def _pad_scenario_features(
        self, spec: DatasetSpec, n_numeric: int | None, n_categorical: int | None
    ) -> None:
        num = [f for f in spec.features if f.dtype in {DType.FLOAT, DType.INTEGER}]
        cat = [f for f in spec.features if f.dtype in {DType.CATEGORY, DType.ORDINAL}]
        extra: list[FeatureSpec] = []
        if n_numeric and n_numeric > len(num):
            extra += self._synthetic_features(n_numeric - len(num), 0)
        if n_categorical and n_categorical > len(cat):
            extra += self._synthetic_features(0, n_categorical - len(cat))
        # Rename synthetic extras to avoid clashing.
        base = len(spec.features)
        for i, f in enumerate(extra):
            f.name = f"extra_{f.dtype.value}_{base + i + 1}"
        spec.features.extend(extra)


def get_planner() -> Agent:
    """Return the configured planner backend."""

    if settings.planner_backend == "llm":
        try:
            from app.agents.llm_planner import LLMPlanner

            return LLMPlanner()
        except Exception as exc:  # pragma: no cover - optional path
            logging.getLogger("dataset_agent").warning(
                "LLM planner unavailable (%s); falling back to heuristic", exc
            )
    return HeuristicPlanner()
