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
| `CELERY_TASK_ALWAYS_EAGER` | Run scraping inline (no broker) | `true` |

## Usage

```bash
# Show resolved configuration
deep-agent config

# Run deep research (writes a markdown report to docs/)
deep-agent research "Impact of GLP-1 drugs on healthcare costs"

# Limit the research loop and choose an output directory
deep-agent research "Quantum error correction progress in 2024" -n 2 -o docs
```

### Distributed scraping with Celery (optional)

By default scraping runs inline. To fan out across workers, set
`CELERY_TASK_ALWAYS_EAGER=false`, point `CELERY_BROKER_URL` at a running
Redis instance, and start a worker:

```bash
celery -A deep_agent.tasks.celery_app:celery_app worker --loglevel=info
```

## Logging

Logs stream to the console (via `rich`) and to a rotating file at
`logs/deep_agent.log`. Control verbosity with `LOG_LEVEL`.

## Extending

- **New LLM provider** — add a builder in `deep_agent/llm/factory.py`.
- **New search provider** — implement `SearchClient` and register it in
  `deep_agent/search/factory.py`.
- **New agent** — subclass `BaseAgent`, then wire it into `graph.py`.
