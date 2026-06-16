# Book Review Aggregator — Backend

A **multi-agent** Python service that researches a book on the web and returns
the author/book summary plus aggregated, verified reviews from many source types
(readers, critics, companies, celebrities). Built with FastAPI and OpenAI.

> Scope of this pass: backend agents + API only. Authentication and the React
> frontend (which will consume `/analyze` and the export endpoints) come later.

## Architecture

```
            ┌──────────────┐
 title ──▶  │ SearchAgent  │ ── web search (Tavily / SerpAPI / mock)
            └──────┬───────┘
                   │ raw sources
        ┌──────────┴───────────┐
        ▼                      ▼
 ┌──────────────┐      ┌──────────────┐
 │ SummaryAgent │      │ ReviewAgent  │  (categorize: reader/critic/
 └──────┬───────┘      └──────┬───────┘   company/celebrity)
        │  BookInfo           │  Reviews
        └──────────┬──────────┘
                   ▼
            ┌──────────────┐
            │ VerifierAgent│  sanity-check claims vs. sources
            └──────┬───────┘
                   ▼
              BookReport ──▶ JSON / Markdown / PDF
```

The `Orchestrator` (`app/agents/orchestrator.py`) wires these together.

## Key design choices

- **Runs offline.** Without `OPENAI_API_KEY` the LLM wrapper returns deterministic
  mock JSON; without a search key the search layer returns mock results. The full
  pipeline and tests run with zero external calls.
- **Pluggable search.** `SEARCH_PROVIDER=tavily|serpapi|mock`. Missing key ⇒ mock.
- **Verifier agent** ("sanity check") fact-checks the summary and reviews against
  the gathered sources and flags unsupported claims.

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in OPENAI_API_KEY + a search key
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

## API

| Method | Path               | Description                                   |
|--------|--------------------|-----------------------------------------------|
| GET    | `/health`          | Status + which LLM/search backends are active |
| POST   | `/analyze`         | Run the pipeline, return a `BookReport` (JSON)|
| POST   | `/export/markdown` | Same pipeline, returns a `.md` download       |
| POST   | `/export/pdf`      | Same pipeline, returns a `.pdf` download      |

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

## Tests

```bash
cd backend
pip install pytest
PYTHONPATH=. pytest -q          # runs fully offline
```
