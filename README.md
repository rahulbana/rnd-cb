# Deep Research Agent

A long-horizon agentic research system that produces **analyst-grade reports** on
companies, markets, and technologies. It runs a LangGraph
`plan → search → read → reflect → synthesize` loop that iterates until the
evidence is sufficient (or a budget cap kicks in), then writes a validated report
with numbered citations, comparison tables, and an executive summary.

The design goal is the hard part of production agents: **long-horizon workflows
with real error recovery** — iteration/cost caps that kill runaway research,
Postgres checkpointing so a 20-minute run survives a crash, and an LLM-as-judge
factuality gate on the output.

---

## Architecture

```
                    ┌──────────────────────── reflection loop ─────────────────────────┐
                    │                                                                   │
  START → [plan] → [search] → [read] → [reflect] ──(gaps remain & budget left)──────────┘
                    │                        │
                    │                        └──(coverage sufficient / capped)──→ [synthesize] → END
                    │
      sub-questions + queries          full-text extraction        gap analysis + re-plan
```

| Node | Responsibility |
|------|----------------|
| **plan** | Decompose the topic into 4–7 sub-questions and seed search queries. |
| **search** | Fan out queries across every enabled backend; dedup + credibility-score results. |
| **read** | Fetch full text for the most credible unread sources (snippet → evidence). |
| **reflect** | Judge sufficiency, identify concrete gaps, and generate targeted re-plan queries. |
| **synthesize** | Write the structured report; citations are repaired deterministically. |

State is a `TypedDict` checkpointed after every super-step, so the loop is fully
resumable by `thread_id` (= job id).

### Layout

```
app/
  config.py              # env-driven settings
  models/                # Pydantic domain + report schemas (the validated deliverable)
  search/                # backend interface + Tavily/Serper/Exa/arxiv + aggregator
  dedup.py               # URL canonicalization + near-duplicate title collapse
  credibility.py         # transparent heuristic source scoring (no LLM)
  budget.py              # iteration + cost caps (kills runaway research)
  graph/
    state.py             # LangGraph state + reducers (source-merge dedups on write)
    builder.py           # graph topology + reflection conditional edge
    checkpointer.py      # Postgres (durable) or in-memory checkpointer
    citations.py         # deterministic citation normalization (pure, tested)
    nodes/               # plan / search / read / reflect / synthesize
  eval/factuality.py     # LLM-as-judge grounding score
  export/                # Word (.docx) + PDF exporters
  jobs/manager.py        # async job queue + progress pub/sub
  llm.py                 # langchain-anthropic wrapper + token accounting
  observability.py       # Langfuse tracing (optional)
  main.py                # FastAPI + SSE streaming
  cli.py                 # terminal entry point
frontend/index.html      # live progress + report viewer (SSE)
tests/                   # pure-logic unit tests (dedup, credibility, budget, citations, report)
```

---

## How the spec maps to the code

| Requirement | Where |
|-------------|-------|
| Plan → search → read → reflect → synthesize loop | `app/graph/builder.py`, `app/graph/nodes/` |
| Multiple search backends (Tavily, Serper, Exa, arxiv) | `app/search/*.py` behind one `SearchBackend` interface |
| Source dedup + credibility scoring | `app/dedup.py`, `app/credibility.py`, applied in `app/search/aggregator.py` |
| Reflection node identifies gaps and re-plans | `app/graph/nodes/reflect.py` (+ deterministic `route_after_reflect`) |
| Report with numbered citations, tables, exec summary | `app/models/report.py`, `app/graph/nodes/synthesize.py` |
| Async job queue + progress streaming | `app/jobs/manager.py`, SSE in `app/main.py` |
| Iteration cap + cost cap (kills runaway research) | `app/budget.py`, enforced in `reflect` router |
| Checkpointing survives a crash | `app/graph/checkpointer.py` (Postgres via `AsyncPostgresSaver`) |
| LLM-as-judge factuality eval | `app/eval/factuality.py` |
| Structured output validated with Pydantic | `ResearchReport` + strict validators, `ReportDraft` → `normalize_citations` |
| Word/PDF export | `app/export/docx_export.py`, `app/export/pdf_export.py` |
| Langfuse observability | `app/observability.py` (callback handler threaded through every LLM call) |

---

## Quickstart

### 1. Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env      # then fill in ANTHROPIC_API_KEY and any search keys
```

Only `ANTHROPIC_API_KEY` is strictly required. Search backends are opt-in: the
aggregator uses whatever has a key, plus keyless **arxiv** always. Without
`DATABASE_URL` it falls back to an in-memory checkpointer (no crash recovery).

### 2. Optional: Postgres for durable checkpoints

```bash
make db-up          # docker compose up -d postgres
# set DATABASE_URL=postgresql://research:research@localhost:5432/research in .env
```

### 3. Run the API

```bash
make run            # uvicorn app.main:app --reload --port 8000
open http://localhost:8000
```

Or run a one-shot from the terminal:

```bash
research "Nvidia's data-center GPU moat" --depth deep --export report.pdf
```

---

## HTTP API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/research` | Submit a job → `{ job_id, status }` (202). |
| `GET`  | `/research/{id}/stream` | **SSE** progress stream (replays history, then tails). |
| `GET`  | `/research/{id}` | Job status + full report JSON + factuality score. |
| `GET`  | `/research/{id}/report.md` | Report as Markdown. |
| `GET`  | `/research/{id}/export?format=pdf\|docx` | Download the report. |
| `POST` | `/research/{id}/cancel` | Cancel a running job. |
| `GET`  | `/healthz` | Config/liveness (enabled backends, checkpointer, etc.). |

Submit:

```bash
curl -sX POST localhost:8000/research -H 'content-type: application/json' -d '{
  "topic": "The competitive landscape for vector databases",
  "audience": "a VC evaluating a Series B",
  "depth": "standard",
  "focus_areas": ["moat", "pricing", "open-source dynamics"]
}'
```

Stream progress:

```bash
curl -N localhost:8000/research/<job_id>/stream
```

Each SSE event is a `ProgressEvent` (`phase`, `message`, `iteration`,
`sources_found`, `usd_spent`, `status`).

---

## Safety & recovery design

- **Runaway protection.** `BudgetTracker` enforces an iteration cap *and* a USD
  cost cap (estimated from token usage + per-search charges). The reflection
  router refuses another loop once either is hit; the job is marked
  `killed_budget` if gaps remained. Search fan-out also tapers as budget depletes.
- **Crash recovery.** With Postgres configured, every node's output is
  checkpointed. Re-invoking the graph with the same `thread_id` resumes from the
  last completed step rather than restarting the (expensive) run.
- **No fabricated citations.** The LLM writes into a permissive `ReportDraft`;
  `normalize_citations` drops any citation that doesn't resolve to a real
  retrieved source, renumbers contiguously, and rewrites inline `[n]` markers to
  match. The final `ResearchReport` then passes strict Pydantic validators.
- **Grounding gate.** `judge_report` runs an independent judge model over the
  report's claims vs. the retrieved sources and returns a 0–1 factuality score
  (SUPPORTED / PARTIAL / UNSUPPORTED / CONTRADICTED breakdown).

---

## Testing

```bash
make test        # pytest -q
```

The suite covers the deterministic core that must never regress: URL
canonicalization + dedup, credibility ordering, budget/cost caps, report/table
validation, and — most importantly — citation normalization (dropping
fabricated citations, renumbering, duplicate collapse, URL-fallback resolution).
These run without any API keys or network access.

---

## Configuration reference

See `.env.example`. Key knobs:

| Var | Default | Meaning |
|-----|---------|---------|
| `SMART_MODEL` / `FAST_MODEL` | sonnet / haiku | Models for synthesis+judging vs. cheap nodes. |
| `MAX_ITERATIONS` | 5 | Hard cap on reflection loops. |
| `MAX_USD_COST` | 2.50 | Hard cap on estimated spend per run. |
| `MAX_SEARCHES_PER_ITERATION` | 6 | Fan-out width per iteration. |
| `MAX_SOURCES` | 40 | Cap on retained sources (bounds context growth). |
| `DATABASE_URL` | — | Postgres DSN; unset ⇒ in-memory checkpointer. |
| `LANGFUSE_*` | — | Enable tracing when both keys are set. |

Depth presets (`quick`/`standard`/`deep`) map to 2/4/6 iterations and can be
overridden per-request via `max_iterations` / `max_usd_cost`.
