# Deep Search Agent

A **deep web-research agent** built with **LangGraph + LangChain + OpenAI**, fronted
by a **React (Vite)** UI that visualises what the agent is doing in real time.

Given a user question, the agent:

1. **Plans** — the LLM decomposes the question into multiple focused sub-queries.
2. **Searches** — each sub-query is run against the web (Tavily or DuckDuckGo).
3. **Synthesizes** — the LLM writes a cited Markdown report from the collected sources.

Every step (which node is running, which tool/model is being used, each source
found, and the report streaming in token-by-token) is streamed to the browser
over **Server-Sent Events**, so you can watch the backend work live.

```
┌──────────────┐   POST /api/search (SSE)   ┌─────────────────────────────┐
│  React (Vite)│ ◀────────────────────────▶ │  FastAPI                    │
│  - timeline  │   node/tool/source/token   │   └─ LangGraph agent        │
│  - resources │        events              │       plan → search → synth │
│  - report    │                            │   OpenAI + Tavily/DuckDuckGo │
└──────────────┘                            └─────────────────────────────┘
```

## Project layout

The backend is organised into clean, swappable layers (config/transport,
schemas, providers, agent, services, API):

```
backend/app/
  main.py                  create_app() factory + ASGI entrypoint
  core/                    cross-cutting concerns
    config.py              pydantic-settings Settings (single source of config)
    logging.py             structured logging setup
    exceptions.py          app-specific exception hierarchy
  schemas/                 pydantic models
    search.py              request/response models
    source.py              Source / SearchResult / RawResult
    events.py              EventType enum (SSE wire contract)
  providers/               pluggable integrations (registry + factory each)
    llm/                   base + openai_provider + factory
    search/                base + tavily + duckduckgo + factory
  agent/                   LangGraph agent
    state.py               graph state
    prompts.py             centralised prompt templates
    nodes/                 planner / searcher / synthesizer (one file each)
    graph.py               wiring (plan → search → synthesize)
  services/                orchestration
    event_bus.py           async queue → SSE bridge
    search_service.py      runs the agent, yields a stream of events
  api/                     transport layer
    deps.py                FastAPI dependency injection
    router.py              aggregate router
    routes/                health + search endpoints

frontend/src/
  App.jsx                  thin composition root
  config.js                runtime config from VITE_* env vars
  constants/events.js      EventType + node labels (mirrors backend contract)
  api/
    sse.js                 SSE frame parser (async generator)
    searchApi.js           streamSearch() / getHealth()
  hooks/
    useDeepSearch.js       run state machine (reducer + event reduction)
  utils/format.js          hostname / timestamp / markdown download helpers
  features/
    search/SearchBox.jsx
    timeline/              AgentTimeline + EventItem
    resources/             ResourceList + ResourceItem
    report/                Report + ReportActions
```

### Extending it

* **Add an LLM vendor** — implement `BaseLLMProvider` and
  `register_llm_provider("name", Builder)`; set `LLM_PROVIDER=name`.
* **Add a search backend** — implement `BaseSearchProvider` and
  `register_search_provider("name", Builder)`; set `SEARCH_PROVIDER=name`.
* **Add a graph step** — drop a node in `agent/nodes/` and wire it in `graph.py`.

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and set OPENAI_API_KEY (TAVILY_API_KEY is optional)

uvicorn app.main:app --reload --port 8000
```

The backend runs at `http://localhost:8000`. Health check: `GET /api/health`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` to the backend.

## Configuration

| Variable            | Default       | Description                                            |
| ------------------- | ------------- | ------------------------------------------------------ |
| `OPENAI_API_KEY`    | —             | **Required.** OpenAI API key.                          |
| `OPENAI_MODEL`      | `gpt-4o-mini` | Chat model for planning + synthesis.                   |
| `TAVILY_API_KEY`    | —             | If set, Tavily is used for search (higher quality).    |
| `SEARCH_PROVIDER`   | `auto`        | `auto` \| `tavily` \| `duckduckgo`.                    |
| `NUM_SUBQUERIES`    | `4`           | Default number of sub-queries the planner generates.   |
| `RESULTS_PER_QUERY` | `4`           | Web results fetched per sub-query.                     |
| `FRONTEND_ORIGIN`   | `*`           | CORS origin for the API.                               |

> Without a `TAVILY_API_KEY`, the agent automatically falls back to DuckDuckGo,
> which needs no key — so it works out of the box with just an OpenAI key.

## Observability

Built-in application + agent observability:

* **Health probes**
  * `GET /api/health` — status snapshot (version, uptime, model, provider)
  * `GET /api/health/live` — liveness probe (process is up)
  * `GET /api/health/ready` — readiness probe (deps configured; returns 503 if not)
* **Prometheus metrics** — `GET /metrics` (root, for scraping):
  * HTTP: `http_requests_total`, `http_request_duration_seconds`, `http_requests_in_progress`
  * Agent: `agent_runs_total{status}`, `agent_run_duration_seconds`, `agent_runs_in_progress`,
    `agent_sources_found`, `agent_node_duration_seconds{node}`
  * Providers: `search_calls_total{provider,status}`, `search_results_total{provider}`,
    `llm_calls_total{model,kind}`, `llm_tokens_streamed_total{model}`
* **Access logs** — one structured line per request (`METHOD path -> status (ms)`),
  via a pure-ASGI middleware that doesn't buffer the SSE stream.
* **Per-run summary** — a `stats` SSE event + log line at the end of each run
  (duration, sub-queries, sources, report size). The UI shows these as a stat row.

Point Prometheus at `/metrics` and wire `/api/health/live` + `/api/health/ready`
to your orchestrator's liveness/readiness probes.

A ready-to-run **Prometheus + Grafana** stack with a pre-built dashboard lives in
[`ops/`](ops/README.md):

```bash
cd backend && uvicorn app.main:app --port 8000   # exposes /metrics
cd ops && docker compose up -d                    # Grafana :3000, Prometheus :9090
```

Or import `ops/grafana/deep-search-dashboard.json` into an existing Grafana.

## Run history (tracing)

Every run is persisted to a local **SQLite** store (`data/runs.db` by default) —
the user query, generated sub-queries, every step, sources, the final report,
status, and timing. The React app's **History** tab lists past runs and drills
into any run's full trace (query → sub-queries → steps → sources → report).

* `GET /api/runs?limit=N` — list recent runs (summaries)
* `GET /api/runs/{id}` — full run record (steps, sources, report)

Toggle with `PERSIST_RUNS` / `RUNS_DB_PATH` in `.env`. This is *content* tracing
(what each run did), complementing the *aggregate* Prometheus metrics above.

### LangSmith (optional)

Because the agent is built on LangChain/LangGraph, you get full step-level
tracing in [LangSmith](https://smith.langchain.com) by setting a few env vars —
no code changes. It's **off by default** since it sends run content (including
user queries) to LangSmith's cloud:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=deep-search-agent
```

Runs are tagged `deep-search` and carry `run_id` + `query` metadata for search.

## API

`POST /api/search` → `text/event-stream`

Request body:
```json
{ "query": "your question", "num_subqueries": 4 }
```

Streamed event types: `run_start`, `node_start`, `tool_call`, `tool_result`,
`subqueries`, `source`, `token`, `report`, `node_end`, `stats`, `done`, `error`.
