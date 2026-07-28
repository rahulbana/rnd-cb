# Architecture

## Overview

The system is a linear pipeline of small, single-responsibility **agents** wired
by an **orchestrator**. Everything centres on one declarative contract, the
`DatasetSpec`: the planner produces it from natural language, and every
downstream agent reads and/or refines it. Because a run is fully determined by
`(spec, seed)`, generation is reproducible and each stage is independently
testable.

```
        Natural language prompt
                  │
                  ▼
          Planner Agent            (prompt -> DatasetSpec)
                  │
                  ▼
          Schema Agent             (unique names, primary key, target)
                  │
                  ▼
          Feature Agent            (draw each column from its distribution)
                  │
                  ▼
       Correlation Agent           (impose feature dependencies)
                  │
                  ▼
          Target Agent             (synthesise a learnable label)
                  │
                  ▼
          Quality Agent            (inject missing / dupes / outliers / noise)
                  │
        ┌─────────┼───────────┬─────────────┐
        ▼         ▼           ▼             ▼
   Validation    EDA      Evaluation   Documentation
        └─────────┴───────────┴─────────────┘
                  │
                  ▼
           Export Agent            (csv / parquet / json / excel / sqlite / sql)
```

## The `DatasetSpec` contract

Defined in `app/models/spec.py` (Pydantic v2). Key pieces:

- `task_type` — classification / regression / clustering / time series.
- `features: list[FeatureSpec]` — each column's logical type, distribution and
  parameters, categories/weights, bounds, and description.
- `target: TargetSpec` — label name, positive rate / number of classes, and
  `signal_strength` (0..1) controlling how learnable the label is.
- `correlations: list[CorrelationSpec]` — desired linear dependencies.
- `quality: QualitySpec` — missing/duplicate/outlier/noise rates.
- `random_seed`.

Because the whole plan is declarative and serialisable, it doubles as the
human-in-the-loop review artifact: `POST /plan` returns it, a user edits it, and
`POST /generate/spec` builds from the edited version.

## Agents

| Agent           | Responsibility                                                        |
| --------------- | --------------------------------------------------------------------- |
| `Planner`       | NL → `DatasetSpec`. Heuristic (offline) or LLM backend.               |
| `Schema`        | Unique/valid names, primary key, target de-collision, weight norm.    |
| `Feature`       | Draw each column independently from its distribution (numpy/Faker).   |
| `Correlation`   | Rewrite target columns as a blend of source + noise to hit a target r.|
| `Target`        | Build a label as a tunable function of the features (+ noise).        |
| `Quality`       | Inject missingness, duplicates, outliers, and Gaussian noise.         |
| `Validation`    | Structural + statistical checks → `ValidationReport`.                 |
| `EDA`           | Summaries, correlations, missingness, target distribution (dict). Exported as a runnable Jupyter notebook (`app/utils/notebook.py`). |
| `Evaluation`    | Train a baseline model; report metrics + ML-readiness score.          |
| `Documentation` | Data dictionary, dataset card, JSON schema.                           |
| `Export`        | Write dataset + docs in many formats.                                 |

## Why a plain pipeline (and how LangGraph slots in)

The design calls for a LangGraph DAG. The reference orchestrator
(`app/graph/orchestrator.py`) is instead an explicit Python pipeline so the
platform runs and tests with **zero heavy dependencies and no event loop**. The
agents are plain objects with a `run(...)` method, so a LangGraph graph can wrap
the exact same agent instances as nodes without changing them — the pipeline is
the reference wiring, not a constraint.

## Planner backends

`get_planner()` returns a backend based on `PLANNER_BACKEND`:

- **`heuristic`** (default, `app/agents/planner.py`): keyword/regex parsing plus
  the domain scenario library (`app/prompts/scenarios.py`). Extracts row counts
  (`"500,000"`, `"250k"`, `"1.5 million"`), task type, positive/event rates,
  feature counts, and data-quality signals. No network, no key.
- **`llm`** (`app/agents/llm_planner.py`): asks an LLM to emit the spec as JSON,
  validates it with Pydantic, and falls back to the heuristic planner on any
  error. Default provider is **OpenAI** (`LLM_PROVIDER=openai`, key from
  `OPENAI_API_KEY`, JSON-mode response); `anthropic` and `litellm` are also
  supported.

Both satisfy the same `plan(prompt) -> DatasetSpec` interface, so nothing
downstream knows which produced the spec.

## Making labels learnable

Random features with a random label yield a dataset no model can learn — a poor
demonstration of "ML-ready". The `TargetAgent` therefore builds a linear (or
optionally non-linear) score from the feature columns, standardises it, and
blends it with noise per `signal_strength`:

```
latent = signal_strength * signal_score + (1 - signal_strength) * noise
```

- **Classification** thresholds `latent` at the quantile that yields the
  requested positive rate (exact class balance, monotonic signal).
- **Multiclass** takes the argmax of several competing scores.
- **Regression** maps `latent` onto an interpretable positive scale.
- **Clustering** assigns ground-truth segments via KMeans on the features.
- **Time series** adds trend + seasonality + a feature-driven component.

The `EvaluationAgent` then trains a baseline (random forest / logistic / linear)
and reports metrics, so the ML-readiness score reflects genuine learnability
rather than an assumption.

## Extending

- **New domain** → add an entry to `SCENARIOS` in `app/prompts/scenarios.py`.
- **New distribution** → extend `sample_distribution` in `app/utils/rng.py` and
  the `Distribution` enum.
- **New export format** → add a handler in `app/agents/exporter.py`.
- **Heavier synthetic data (SDV/CTGAN)** → add an agent implementing the same
  `run(spec, rng) -> DataFrame` shape as `FeatureAgent` and swap it in the
  orchestrator; install via the `synthetic` extra.
- **Scale-out** → wrap `DatasetService` in a Celery task; the design's
  Redis/Celery/observability stack composes around the service unchanged.
