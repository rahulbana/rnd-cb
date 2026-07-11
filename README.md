# Deep Agent

A modular, multi-agent **deep-research CLI** built on **LangGraph**, with
**Celery** for distributed scraping and **Tenacity** for resilient network
calls. Give it a topic and it plans, searches, scrapes, reflects,
fact-checks and writes a fully-cited **Markdown report** to `docs/`.

Both the **LLM provider** (OpenAI / Anthropic) and the **search provider**
(Tavily / Serper) are switchable via configuration.

---

## Architecture

Seven specialised agents are orchestrated as a stateful LangGraph with an
adaptive research loop:

```
planner → search → collector → scraper → reflection ─┐
             ▲                                        │ needs more research
             └────────────────────────────────────────┘
                                  │ evidence sufficient
                                  ▼
                          fact_checker → writer → END
```

| Agent | Responsibility |
| --- | --- |
| **Planner** | Decomposes the topic into sub-topics + targeted search queries. |
| **Search** | Runs queries through the switchable search provider. |
| **Collector** | Deduplicates, ranks and budgets URLs to scrape. |
| **Scraper** | Fetches & cleans page content via Celery tasks (Tenacity retries). |
| **Reflection** | Critiques coverage; loops back for more research if needed. |
| **Fact Checker** | Verifies key claims strictly against gathered sources. |
| **Writer** | Synthesises a cited Markdown report. |

### Project layout

```
deep_agent/
├── cli.py              # Typer CLI entry point
├── config.py           # Pydantic-settings configuration
├── state.py            # LangGraph shared state
├── graph.py            # Graph assembly + runner + report persistence
├── models/schemas.py   # Pydantic data contracts
├── llm/                # Switchable LLM factory (OpenAI / Anthropic)
├── search/             # Switchable search clients (Tavily / Serper)
├── agents/             # The seven agent nodes
├── tasks/              # Celery app + scraping task
└── utils/              # Logging + Tenacity retry policies
```

---

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .          # or: pip install -r requirements.txt
```

## Configuration

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

Key settings (see `.env.example` for the full list):

| Variable | Purpose | Default |
| --- | --- | --- |
| `LLM_PROVIDER` | `openai` or `anthropic` | `openai` |
| `LLM_MODEL` | Model name | `gpt-4o` |
| `SEARCH_PROVIDER` | `tavily` or `serper` | `tavily` |
| `MAX_RESEARCH_ITERATIONS` | Reflection loop ceiling | `3` |
| `CELERY_TASK_ALWAYS_EAGER` | Run scraping/search inline (no broker) | `true` |
| `CHECKPOINT_BACKEND` | `none` / `memory` / `sqlite` | `memory` |
| `CHECKPOINT_DB` | SQLite checkpoint file (when `sqlite`) | `deep_agent_checkpoints.sqlite` |

## Usage

```bash
# Validate configuration (API keys, broker, checkpointer) before running
deep-agent doctor

# Show resolved configuration
deep-agent config

# Run deep research (writes a markdown report to docs/)
deep-agent research "Impact of GLP-1 drugs on healthcare costs"

# Limit the research loop, set a checkpoint thread, choose an output dir
deep-agent research "Quantum error correction progress in 2024" -n 2 -t qec-2024 -o docs
```

`research` runs a **preflight** check first and fails fast with an
actionable message if a required key or the broker is missing (bypass with
`--skip-preflight`).

### Distributed scraping with Celery (optional)

By default scraping runs inline. To fan out across workers, set
`CELERY_TASK_ALWAYS_EAGER=false`, point `CELERY_BROKER_URL` at a running
Redis instance, and start a worker:

```bash
celery -A deep_agent.tasks.celery_app:celery_app worker --loglevel=info
```

### Parallel search

Search queries are fanned out as a Celery `group` (mirroring the scraper),
so with real workers they run in parallel; under eager mode they run inline.

### Checkpointing

Set `CHECKPOINT_BACKEND=sqlite` to persist graph state per `thread_id` to
`CHECKPOINT_DB`. This gives **resumable runs** (a run interrupted by a crash
resumes from the last completed node) and a full **state history** for
inspection. The default `memory` backend keeps this in-process only.

> Note: checkpointing resumes *interrupted* runs — it does not auto-cache a
> fully-completed run, so re-invoking a finished thread re-executes the graph.

## Logging

Logs stream to the console (via `rich`) and to a rotating file at
`logs/deep_agent.log`. Control verbosity with `LOG_LEVEL`.

## Extending

- **New LLM provider** — add a builder in `deep_agent/llm/factory.py`.
- **New search provider** — implement `SearchClient` and register it in
  `deep_agent/search/factory.py`.
- **New agent** — subclass `BaseAgent`, then wire it into `graph.py`.
