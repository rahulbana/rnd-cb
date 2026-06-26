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
  App.jsx                  state + event handling
  api.js                   SSE-over-fetch client
  components/              SearchBox, AgentTimeline, ResourceList, Report
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

## API

`POST /api/search` → `text/event-stream`

Request body:
```json
{ "query": "your question", "num_subqueries": 4 }
```

Streamed event types: `run_start`, `node_start`, `tool_call`, `tool_result`,
`subqueries`, `source`, `token`, `report`, `node_end`, `done`, `error`.
