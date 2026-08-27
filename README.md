# Deep Research Agent

An autonomous, long-running **deep research agent** built on **LangGraph** with
**durable Postgres-checkpointed state**. It plans a research topic, searches the
web (Tavily with a DuckDuckGo fallback), reflects on gaps, iterates, and
synthesizes a cited Markdown report. A **FastAPI** backend streams live progress
over **Server-Sent Events**; a **React (Vite)** frontend renders the run and the
final report.

```
User topic
   │
   ▼
┌──────────┐   ┌──────────┐   ┌───────────┐   gaps?   ┌─────────────┐
│  plan    │──▶│  search  │──▶│  reflect  │──────────▶│  (loop back)│
└──────────┘   └──────────┘   └───────────┘           └─────────────┘
                                    │ sufficient / budget reached
                                    ▼
                             ┌──────────────┐
                             │  synthesize  │──▶ cited Markdown report
                             └──────────────┘
        every step checkpointed to Postgres (resumable, restart-safe)
```

## Why this design

| Concern | Decision | Rationale |
|---|---|---|
| Long-running / resumable | LangGraph `AsyncPostgresSaver` checkpointer | Every node persists state; a run survives process restarts and is resumable by `thread_id`. |
| Bounded cost/latency | `MAX_ITERATIONS` + `MAX_QUERIES_PER_ITERATION` + a hard stop in `reflect` | Autonomous loops must not run away. The model's "sufficient" signal is capped by an explicit budget. |
| Search resilience | Tavily → DuckDuckGo fallback chain | Graceful degradation instead of a hard failure when the primary provider is down/rate-limited; DDG is keyless. |
| Live progress on a slow task | Background task + in-memory pub/sub → SSE, with history replay | The run executes independently of any client; clients connect/reconnect to stream or poll durable state. |
| Model cost | Two tiers: cheap worker model (plan/extract/reflect), stronger synthesis model | Most calls are cheap; only the single final report uses the higher-quality model. |
| Grounding | Findings carry source URLs; synthesis cites numbered sources | Reduces hallucination and makes the report auditable. |

## Project layout

```
backend/
  app/
    core/         config, structured logging, Postgres persistence
    tools/        web search (Tavily + DuckDuckGo fallback)
    agent/        state, prompts, LLM factory, nodes, graph
    services/     research orchestration + SSE event broker
    api/          FastAPI routes + schemas
    main.py       app factory + lifespan
  tests/          unit tests (reducers, routing, events, search fallback)
  Dockerfile  requirements.txt  .env.example
frontend/
  src/            React app (Composer, ProgressTimeline, ReportView, SourcesList)
  vite.config.js  package.json  index.html
docker-compose.yml
```

## Quick start (Docker Compose)

```bash
cp backend/.env.example backend/.env
# edit backend/.env: set OPENAI_API_KEY (and TAVILY_API_KEY for best results)
docker compose up --build
# UI:  http://localhost:5173
# API: http://localhost:8000/docs
```

Compose starts Postgres, the backend, and the Vite dev server (which proxies
`/api` to the backend).

## Local development (without Docker)

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # set OPENAI_API_KEY (+ TAVILY_API_KEY)
# Postgres must be reachable at DATABASE_URL, e.g.:
#   docker run -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=research postgres:16
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

**Tests**

```bash
cd backend && pytest        # pure-logic unit tests, no network/DB needed
```

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/research` | Start a run. Body: `{ "topic": "..." }`. Returns `{ thread_id }` (202). |
| `GET` | `/api/research/{thread_id}` | Durable state snapshot: status, plan, findings count, sources, final report. |
| `GET` | `/api/research/{thread_id}/stream` | SSE stream of progress events (replays history, then live). |
| `DELETE` | `/api/research/{thread_id}` | Cancel a running research task. |
| `GET` | `/health` | Liveness probe. |

**SSE event types:** `run_started`, `planned`, `searched`, `reflected`,
`synthesized`, `completed`, `error`, `cancelled`. Each carries a JSON payload;
`completed` includes `final_report` and `sources`.

Example:

```bash
curl -XPOST localhost:8000/api/research -H 'content-type: application/json' \
  -d '{"topic":"State of agentic AI frameworks in 2025"}'
# {"thread_id":"...","status":"running"}
curl -N localhost:8000/api/research/<thread_id>/stream
```

## Configuration

All settings are environment-driven (see `backend/.env.example`). Key knobs:

- `OPENAI_MODEL` / `OPENAI_SYNTHESIS_MODEL` — worker vs. synthesis models.
- `TAVILY_API_KEY` — omit to run search on DuckDuckGo only.
- `MAX_ITERATIONS`, `MAX_QUERIES_PER_ITERATION`, `MAX_RESULTS_PER_QUERY` — the
  research budget that bounds a long run.
- `DATABASE_URL`, `DB_POOL_*` — Postgres connection + pool sizing.

## Production notes & known limits

- **Single-process SSE broker.** Progress fan-out is in-memory, so run the
  backend as **one process/worker** as shipped. The durable state lives in
  Postgres, so results are never lost — only the *live* stream is
  process-local. To scale horizontally, replace `services/events.py` with Redis
  pub/sub (same interface) and share it across workers.
- **Resumption.** State is checkpointed per node. Re-running the graph with the
  same `thread_id` resumes from the last checkpoint (the current service starts
  fresh runs; wiring an explicit resume endpoint is a small addition).
- **Secrets** stay in the environment, never in source. `.env` is gitignored.
- **Observability.** Structured JSON logs are emitted for every node with
  counts and timings — pipe stdout to your log aggregator. Add OpenTelemetry
  tracing around node calls for per-step latency in production.
- **Guardrails.** For untrusted end-user topics, add an input policy/moderation
  check before `plan`, and a domain allow/deny list on the search tool.
```
