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
| `LLM_MODEL` | Default model name | `gpt-4o` |
| `LLM_FAST_MODEL` | Cheaper model for FAST-tier agents | (= `LLM_MODEL`) |
| `LLM_AGENT_MODELS` | Per-agent model overrides (JSON) | `{}` |
| `LLM_MAX_TOKENS` | Cap output tokens per call | unset |
| `LLM_CACHE_BACKEND` | `none` / `memory` / `sqlite` | `sqlite` |
| `MAX_CONTEXT_CHARS` | Total input-context budget per prompt | `24000` |
| `SEARCH_PROVIDER` | `tavily` or `serper` | `tavily` |
| `MAX_RESEARCH_ITERATIONS` | Reflection loop ceiling | `3` |
| `CELERY_TASK_ALWAYS_EAGER` | Run scraping/search inline (no broker) | `true` |
| `CHECKPOINT_BACKEND` | `none` / `memory` / `sqlite` | `memory` |
| `CHECKPOINT_DB` | SQLite checkpoint file (when `sqlite`) | `deep_agent_checkpoints.sqlite` |
| `RESPECT_ROBOTS` | Honour robots.txt when scraping | `true` |
| `SCRAPE_DELAY_SECONDS` | Min delay between requests to the same domain | `1.0` |
| `STREAM_PROGRESS` | Show live per-node progress in the CLI | `true` |
| `LANGFUSE_ENABLED` | Trace runs to Langfuse | `false` |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | Langfuse credentials | — |
| `LANGFUSE_HOST` | Langfuse endpoint | `https://cloud.langfuse.com` |

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

# Run silently (single invoke) instead of streaming per-node progress
deep-agent research "..." --no-stream
```

`research` runs a **preflight** check first and fails fast with an
actionable message if a required key or the broker is missing (bypass with
`--skip-preflight`).

By default the CLI **streams** live per-node progress (`✓ Planning research`,
`✓ Searching the web`, …); pass `--no-stream` to run with a single silent
`invoke` instead.

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

### Scraper politeness

The scraper honours each site's `robots.txt` (`RESPECT_ROBOTS`) and rate-limits
requests per domain (`SCRAPE_DELAY_SECONDS`) using the configured
`SCRAPE_USER_AGENT`. Disallowed URLs are skipped with a clear reason rather
than fetched. Robots caches and throttle timers are per worker process.

### Checkpointing

Set `CHECKPOINT_BACKEND=sqlite` to persist graph state per `thread_id` to
`CHECKPOINT_DB`. This gives **resumable runs** (a run interrupted by a crash
resumes from the last completed node) and a full **state history** for
inspection. The default `memory` backend keeps this in-process only.

> Note: checkpointing resumes *interrupted* runs — it does not auto-cache a
> fully-completed run, so re-invoking a finished thread re-executes the graph.

### LLM control & optimization

The factory gives fine-grained, per-agent control over models while keeping
calls cheap:

- **Per-agent models** — override any agent's model via `LLM_AGENT_MODELS`,
  e.g. `{"writer":"gpt-4o","reflection":"gpt-4o-mini"}`. Agents also declare a
  tier (`SMART`/`FAST`); FAST agents (e.g. Reflection) use `LLM_FAST_MODEL`
  when set, so lightweight steps run on a cheaper model.
- **Fine-grained params** — `LLM_MAX_TOKENS`, `LLM_TIMEOUT`, `LLM_MAX_RETRIES`
  and `LLM_SEED` (deterministic runs) are applied uniformly.
- **Response caching** — identical LLM calls are served from a cache
  (`LLM_CACHE_BACKEND=sqlite` dedupes across runs; great for reruns and the
  repeated reflection/fact-check prompts within a run).
- **Context budgeting** — prompts to Reflection/Fact-Checker/Writer are capped
  by `MAX_CONTEXT_CHARS` / `PER_SOURCE_CHARS`, cutting input tokens and
  preventing overflow. The Writer cites only the sources that fit the budget.
- **Token logging** — every LLM call logs input/output/total tokens per agent.
- **Lazy models** — LLM-free agents (search/collector/scraper) never build a
  model or require an API key; LLM agents build on first use and are cached
  per `(provider, model)`.

### Tracing & observability (Langfuse)

Set `LANGFUSE_ENABLED=true` with your `LANGFUSE_PUBLIC_KEY` /
`LANGFUSE_SECRET_KEY` (and `LANGFUSE_HOST`) to trace every run to
[Langfuse](https://langfuse.com). A LangChain callback handler is attached
to the graph run, so each node and every LLM call is captured as a span;
runs are grouped by `thread_id` as the Langfuse **session** and tagged
`deep-agent`. Traces are flushed automatically before the CLI exits. When
disabled (the default) there is zero overhead. Verify with `deep-agent doctor`.

## Logging

Logs stream to the console (via `rich`) and to a rotating file at
`logs/deep_agent.log`. Control verbosity with `LOG_LEVEL`.

## Extending

- **New LLM provider** — add a builder in `deep_agent/llm/factory.py`.
- **New search provider** — implement `SearchClient` and register it in
  `deep_agent/search/factory.py`.
- **New agent** — subclass `BaseAgent`, then wire it into `graph.py`.
