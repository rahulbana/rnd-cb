# 📚 Book Review Aggregator

A **multi-agent** application that researches a book across the web and returns
the author/book summary plus **aggregated, verified reviews** from many source
types — everyday readers, professional critics, companies/publishers, and
celebrities. Results can be viewed in the browser and downloaded as **Markdown**
or **PDF**.

- **Backend:** Python · FastAPI · OpenAI (multi-agent pipeline)
- **Frontend:** React · Vite

## How it works

You enter a book title (and optionally the author). A pipeline of specialized
agents does the rest:

```
            ┌──────────────┐
 title ──▶  │ SearchAgent  │ ── web search (Tavily / SerpAPI / mock)
            └──────┬───────┘
                   │ raw sources
        ┌──────────┴───────────┐
        ▼                      ▼
 ┌──────────────┐      ┌──────────────┐
 │ SummaryAgent │      │ ReviewAgent  │  categorize each reviewer as
 └──────┬───────┘      └──────┬───────┘  reader / critic / company / celebrity
        │  BookInfo           │  Reviews
        └──────────┬──────────┘
                   ▼
            ┌──────────────┐
            │ VerifierAgent│  "sanity check": fact-checks the summary and
            └──────┬───────┘  reviews against the gathered sources, flags
                   ▼          unsupported claims, reports a confidence score
              BookReport ──▶ JSON · Markdown · PDF
```

The `Orchestrator` (`backend/app/agents/orchestrator.py`) wires the agents
together and assembles the final `BookReport`.

## Features

- 🔎 **Web research** across multiple sources per book
- 🧑‍🤝‍🧑 **Reviews grouped by source type** — readers, critics, companies, celebrities
- ✅ **Verifier / sanity-check agent** that fact-checks claims against sources
- ⬇️ **Download** the report as Markdown or PDF
- 🧪 **Runs fully offline** — deterministic mock data when no API keys are set,
  so you can develop and test end-to-end with zero external calls
- 🔌 **Pluggable web search** (`tavily` / `serpapi`), auto-fallback to mock

> **Authentication** is intentionally not included yet — it is a planned next step.

## Project structure

```
rnd-cb/
├── backend/                 # FastAPI + OpenAI multi-agent service
│   ├── app/
│   │   ├── agents/          # search, summary, review, verifier, orchestrator
│   │   ├── main.py          # API routes (/analyze, /export/*, /health)
│   │   ├── models.py        # Pydantic schemas
│   │   ├── llm.py           # OpenAI wrapper + offline mock
│   │   ├── web_search.py    # Tavily/SerpAPI + mock fallback
│   │   ├── export.py        # Markdown + PDF rendering
│   │   └── config.py        # env-based settings
│   ├── tests/               # offline end-to-end tests
│   ├── requirements.txt
│   └── README.md            # backend details
└── frontend/                # React (Vite) UI
    ├── src/
    │   ├── App.jsx
    │   ├── api.js
    │   └── components/      # SearchForm, ReportView, ReviewCard
    ├── package.json
    └── README.md            # frontend details
```

## Quick start

### 1. Backend (port 8000)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add OPENAI_API_KEY + a search key (optional)
uvicorn app.main:app --reload --port 8000
```

Runs with mock data out of the box; add keys in `.env` for real results.

### 2. Frontend (port 5173)

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

Vite proxies API calls to the backend on `:8000` — no CORS setup needed in dev.

## API

| Method | Path               | Description                                    |
|--------|--------------------|------------------------------------------------|
| GET    | `/health`          | Status + which LLM/search backends are active  |
| POST   | `/analyze`         | Run the pipeline, return a `BookReport` (JSON) |
| POST   | `/export/markdown` | Same pipeline, returns a `.md` download        |
| POST   | `/export/pdf`      | Same pipeline, returns a `.pdf` download       |

Request body for all POST routes:

```json
{ "title": "The Great Gatsby", "author": "F. Scott Fitzgerald" }
```

Example:

```bash
curl -s localhost:8000/analyze \
  -H 'content-type: application/json' \
  -d '{"title":"Dune"}' | jq
```

## Configuration

Backend environment variables (see `backend/.env.example`):

| Variable            | Default        | Description                                   |
|---------------------|----------------|-----------------------------------------------|
| `OPENAI_API_KEY`    | _(empty)_      | Enables real LLM calls; empty ⇒ offline mock  |
| `OPENAI_MODEL`      | `gpt-4o-mini`  | Chat-completions model                        |
| `SEARCH_PROVIDER`   | `tavily`       | `tavily` \| `serpapi` \| `mock`               |
| `TAVILY_API_KEY`    | _(empty)_      | Required for the Tavily provider              |
| `SERPAPI_API_KEY`   | _(empty)_      | Required for the SerpAPI provider             |
| `CORS_ORIGINS`      | localhost:3000,5173 | Allowed frontend origins                 |

Frontend (see `frontend/.env.example`): `VITE_API_BASE` — backend base URL for
production (leave empty in dev to use the Vite proxy).

## Tests

```bash
cd backend
pip install pytest
PYTHONPATH=. pytest -q          # runs fully offline
```

## Roadmap

- [ ] User authentication (login for the frontend)
- [ ] Persist past reports / history
- [ ] Additional export formats and richer PDF styling
