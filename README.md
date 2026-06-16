# CSV Insight Agent

An autonomous agent that ingests any CSV and analyses it **from multiple
perspectives** — structural, type-based, statistical, distributional,
relational and data-quality — then explains what it understood in plain
English and renders the findings as **interactive charts**.

- **Backend:** Python · FastAPI · pandas / numpy / scipy
- **Reasoning:** OpenAI LLM (with a deterministic, no-key fallback)
- **Frontend:** React (Vite) · Recharts

The agent handles every column type it finds — integers, floats, booleans,
categoricals, free text, datetimes and identifiers — and adapts its analysis
and charts accordingly.

---

## What the agent does

When you upload a CSV, the backend runs a deterministic **profiling engine**
that looks at the data from several independent angles:

| Perspective      | What it extracts |
|------------------|------------------|
| **Structural**   | rows, columns, memory, duplicate rows, overall missingness |
| **Type**         | a *semantic* type per column (integer, float, boolean, categorical, text, datetime, identifier, constant) — smarter than the raw dtype |
| **Statistical**  | mean, std, median, quartiles, skew, kurtosis, zeros/negatives |
| **Distribution** | per-column histograms + IQR-based outlier detection |
| **Relational**   | pairwise correlations, ranked and labelled by strength/direction |
| **Quality**      | missing-value hotspots, constants, imbalanced booleans, ID columns |

That structured profile is then handed to an **OpenAI model** acting as a
senior data analyst, which returns:

- a **narrative** of what the dataset is and what stands out,
- a list of concrete, evidence-backed **inferences**, and
- **suggested questions** to explore next.

If no `OPENAI_API_KEY` is set, a built-in rule-based analyst produces the same
shaped output so the app is fully functional offline.

Finally, the agent emits **declarative chart specs** (type composition,
missing-data map, distributions, category breakdowns, the strongest scatter
relationship, and a correlation heatmap) that the React frontend renders as
interactive, descriptive charts.

---

## Project layout

```
backend/
  app/
    main.py        # FastAPI app + routes (/api/health, /api/analyze)
    analysis.py    # the multi-perspective profiling engine + chart specs
    llm_agent.py   # OpenAI reasoning layer + deterministic fallback
    models.py      # Pydantic response schemas
    config.py      # settings (.env)
  requirements.txt
frontend/
  src/
    App.jsx
    api.js
    components/    # FileUpload, Overview, Inferences, ChartRenderer, ColumnTable, DataPreview
    styles.css
  package.json
```

---

## Running locally

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# optional — enable AI-generated insights
cp .env.example .env
# then put your key in .env:  OPENAI_API_KEY=sk-...

uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` to the
backend, so no CORS configuration is needed during development. Drop a CSV
onto the page and the dashboard fills in.

---

## API

### `GET /api/health`
Readiness probe; also reports whether the LLM is enabled and which model.

### `POST /api/analyze`
Multipart form upload with a `file` field (`.csv` / `.tsv` / `.txt`, ≤ 25 MB).
Returns the full analysis payload:

```jsonc
{
  "overview":  { "rows": 0, "columns": 0, "missing_pct": 0, "type_breakdown": {} },
  "columns":   [ /* per-column ColumnProfile */ ],
  "correlations": [ /* ranked numeric relationships */ ],
  "charts":    [ /* declarative ChartSpec objects */ ],
  "inferences": [ "…" ],
  "narrative": "…",
  "suggested_questions": [ "…" ],
  "llm_used": true,
  "sample_rows": [ /* first 20 parsed rows */ ]
}
```

---

## Configuration (`backend/.env`)

| Variable          | Default        | Purpose |
|-------------------|----------------|---------|
| `OPENAI_API_KEY`  | *(empty)*      | enables AI insights; empty → deterministic fallback |
| `OPENAI_MODEL`    | `gpt-4o-mini`  | model used for the analyst |
| `OPENAI_BASE_URL` | *(unset)*      | point at an OpenAI-compatible gateway |
| `CORS_ORIGINS`    | localhost dev  | comma-separated allowed origins |
| `MAX_UPLOAD_BYTES`| `26214400`     | upload size cap (25 MB) |

---

## Sample data

A tiny example (`backend/sample_data.csv`) is included so you can try the agent
immediately without hunting for a dataset.
