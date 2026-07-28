# ML Dataset Generator Agent

An agentic AI platform that turns a **natural-language request** into a
complete, **ML-ready dataset** — plus schema, data dictionary, EDA, validation,
a baseline model evaluation, an ML-readiness score, and multi-format exports.

> _"Create a fraud detection dataset with 500,000 records, 25 numerical
> features, 10 categorical features, 2% fraud rate."_ → a downloadable,
> analysed, documented dataset.

Think **ChatGPT + Kaggle dataset generator + data engineer + ML expert**, as a
single pipeline.

## Highlights

- **Runs fully offline.** The default planner parses prompts with a
  keyword/regex + domain-scenario engine — **no API key required**. An
  optional LLM planner (`PLANNER_BACKEND=llm`) is a drop-in behind the same
  interface.
- **Learnable, not random.** The target agent synthesises labels as a tunable
  function of the features (`signal_strength`), so a model actually has
  something to learn. Every run reports baseline metrics + an ML-readiness
  score.
- **Reproducible.** A run is fully determined by `(spec, seed)`.
- **Multi-agent architecture.** Planner → Schema → Feature → Correlation →
  Target → Quality → Validation → EDA → Evaluation → Documentation → Export.
- **Many formats.** CSV, Parquet, JSON, Excel, SQLite, and portable SQL DDL.
- **Interfaces.** Python API, CLI, and FastAPI service.

## Install

Requires **Python 3.10+**.

### 1. Create and activate a virtual environment

```bash
# From the project root:
python3 -m venv .venv

# Activate it:
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows (PowerShell/CMD)
```

Your prompt should now be prefixed with `(.venv)`. Deactivate any time with
`deactivate`.

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt      # core stack + OpenAI planner

# optional extras:
pip install -e ".[synthetic]"        # SDV / imbalanced-learn
pip install -e ".[llm]"              # extra providers: anthropic / litellm
```

### 3. Configure (optional — only for the LLM planner)

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY=sk-...  (and PLANNER_BACKEND=llm)
```

Skip this step to run the fully offline heuristic planner (no API key needed).

### 4. Run it

```bash
# CLI — generate a dataset:
python -m app.cli generate "fraud detection dataset with 5000 rows and 2% fraud rate"

# Or start the API:
uvicorn app.api.main:app --reload    # http://127.0.0.1:8000/docs

# Or run the tests to verify the install:
python -m pytest -q
```

See [Quickstart](#quickstart) below for more examples.

## Quickstart

### CLI

```bash
# Inspect the plan the agent infers (human-in-the-loop review step):
python -m app.cli plan "telecom churn dataset with 250k customers and 12% churn"

# Generate + analyse + export:
python -m app.cli generate \
  "Create a fraud detection dataset with 50000 records and 2% fraud rate." \
  --format csv --format parquet --out-dir datasets

# Watch each pipeline step as it runs:
python -m app.cli generate "telecom churn dataset with 12% churn" --verbose

# List built-in domain scenarios:
python -m app.cli scenarios
```

With `--verbose` (`-v`) the pipeline narrates every stage:

```
=== Generating 'fraud_dataset' (binary_classification, 50000 rows, seed=42) ===
▶ Step 1 — Schema: finalise columns, keys, and types
[schema] schema finalised with 37 columns
▶ Step 2 — Features: draw each column from its distribution
[feature] generated 50000 rows x 37 base columns
▶ Step 3 — Correlations: impose feature dependencies
▶ Step 4 — Target: synthesise the label from the features
▶ Step 5 — Quality: inject missing/duplicates/outliers/noise
▶ Step 6 — Validation: structural & statistical checks
▶ Step 7 — EDA: compute summaries, correlations, target distribution
▶ Step 8 — Evaluation: train baseline model, score ML-readiness
▶ Step 9 — Documentation: build the data dictionary
▶ Step 10 — Export: write csv, parquet + reports
✓ Done — 50000 rows written to datasets/fraud_dataset
```

### Python

```python
from app.services.generator import DatasetService

service = DatasetService()
result = service.generate_from_prompt(
    "Create a regression dataset for predicting house prices with 30 features.",
    rows=100_000,
    formats=["csv", "parquet"],
)

print(result.summary())
print(result.evaluation.metrics)          # {'r2': ..., 'rmse': ..., 'mae': ...}
print(result.evaluation.ml_readiness_score)
```

### API

```bash
uvicorn app.api.main:app --reload
```

| Method | Path             | Purpose                                  |
| ------ | ---------------- | ---------------------------------------- |
| POST   | `/plan`          | Infer a `DatasetSpec` from a prompt      |
| POST   | `/generate`      | Plan + generate + analyse + export       |
| POST   | `/generate/spec` | Generate from an edited spec (review UX) |
| GET    | `/scenarios`     | List domain templates                    |
| GET    | `/health`        | Liveness probe                           |

```bash
curl -s localhost:8000/generate \
  -H 'content-type: application/json' \
  -d '{"prompt":"loan default dataset with 8% default","rows":20000,"formats":["csv"]}'
```

## Using an LLM planner (OpenAI)

The default planner is offline. To have an LLM infer the spec instead, configure
a `.env` file (loaded automatically; `.env` is git-ignored so your key stays
local):

```bash
cp .env.example .env
# then edit .env:
#   PLANNER_BACKEND=llm
#   LLM_PROVIDER=openai
#   LLM_MODEL=gpt-4o-mini
#   OPENAI_API_KEY=sk-...
#   OPENAI_BASE_URL=...        # optional, for Azure/OpenAI-compatible gateways
```

Equivalent shell environment variables also work and take precedence over
`.env`. `openai` is already in `requirements.txt`; real environment variables
override `.env` values so container/CI config is never clobbered.

The LLM is asked for a strict JSON `DatasetSpec` (OpenAI JSON mode), validated
with Pydantic. On any error it falls back to the heuristic planner, so the
pipeline never hard-fails. `anthropic` and `litellm` providers are also
supported via `LLM_PROVIDER`.

## What a run produces

Each run writes into its own subdirectory, `datasets/<dataset_name>/`, so a
dataset's files stay grouped together (the path is also returned as
`output_dir` in the run summary):

```
datasets/
└── fraud_dataset/
    ├── fraud_dataset.csv
    ├── fraud_dataset.parquet
    ├── fraud_dataset_eda.ipynb
    ├── fraud_dataset_CARD.md
    ├── fraud_dataset_data_dictionary.json
    └── fraud_dataset_schema.json
```

For a prompt, the pipeline emits:

- the **dataset** in every requested format,
- a **data dictionary** (`*_data_dictionary.json`),
- a **runnable EDA notebook** (`*_eda.ipynb`): a Jupyter notebook with live code
  cells (summary stats, missing-value map, target distribution, numeric
  histograms, correlation heatmap, categorical breakdowns) plus the precomputed
  EDA summary embedded as markdown. Open it with `jupyter lab` / `jupyter
  notebook` and run all cells,
- a **dataset card** (`*_CARD.md`),
- a **JSON schema** of the spec (`*_schema.json`),
- a **validation report** and a **baseline evaluation** with an
  **ML-readiness score** (0–100).

## Supported tasks

Binary / multiclass classification, regression, clustering, and time series,
across curated domain scenarios (banking/fraud, telecom/churn, lending,
real-estate, insurance, healthcare, HR attrition, retail forecasting, customer
segmentation) — or fully generic when no scenario matches.

## Project layout

```
app/
  agents/      planner, schema, feature, correlation, target, quality,
               validation, eda, evaluation, documentation, exporter
  graph/       pipeline orchestrator (LangGraph-ready)
  services/    high-level facade (DatasetService)
  models/      Pydantic spec + result artifacts
  prompts/     domain scenario library
  api/         FastAPI app
  cli.py       Typer CLI
configs/       default.yaml
tests/         pytest suite
docs/          architecture notes
```

## Design & extensibility

See [`docs/architecture.md`](docs/architecture.md) for the agent pipeline, the
`DatasetSpec` contract, and how to plug in an LLM planner, LangGraph
orchestration, or heavier synthetic-data backends (SDV/CTGAN) without touching
the rest of the system.

## Tests

```bash
python -m pytest -q
```

## License

MIT.
