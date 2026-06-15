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

```
backend/
  app/
    main.py            FastAPI app + SSE streaming endpoint
    config.py          Env-based settings
    events.py          Async event emitter (queue → SSE)
    agent/
      graph.py         LangGraph wiring (plan → search → synthesize)
      state.py         Graph state schema
      nodes.py         Node implementations (LLM planning + synthesis)
      tools.py         Web search tools (Tavily / DuckDuckGo)
  requirements.txt
  .env.example
frontend/
  src/
    App.jsx            State + event handling
    api.js             SSE-over-fetch client
    components/        SearchBox, AgentTimeline, ResourceList, Report
```

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
