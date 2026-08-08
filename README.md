# Ecommerce AI Assistant

A personal **agentic AI application** built on the OpenAI LLM with a **custom,
framework-free function-calling loop** (no LangGraph / LangChain). It plays the
role of an assistant for an ecommerce business owner and can reason across six
tools:

| Tool | What it does |
| --- | --- |
| **Database** (`db_get_schema`, `db_run_sql`) | Query a local ecommerce SQL database (SQLite now, Postgres-ready). Read-only by default. |
| **Web search** (`web_search`) | Quick web lookups via Tavily. |
| **Deep web search** (`deep_web_search`) | In-depth multi-source research with full-page extraction via Tavily. |
| **File system** (`fs_*`) | Read/write/list/delete files inside a sandboxed workspace. |
| **Email** (`send_email`) | Send email over SMTP (send-only, with a dry-run mode). |
| **Calculator** (`calculator`) | Safe, exact arithmetic (AST-based, no `eval`). |

Everything is plain Python — the whole agent loop is ~60 readable lines in
[`app/agent.py`](app/agent.py).

## Architecture

```
app/
  __main__.py     Rich-powered CLI REPL (python -m app)
  config.py       One dataclass, loaded from env / .env
  llm.py          Thin OpenAI Chat Completions wrapper
  agent.py        The custom function-calling loop + system prompt
  tools/
    base.py       Tool + ToolRegistry (JSON-Schema in, error-isolated dispatch)
    database.py   SQLite tool (swappable to Postgres)
    web_search.py / deep_search.py   Tavily quick + deep research
    filesystem.py Sandboxed file access
    email_tool.py SMTP send-only
    calculator.py AST-based safe evaluator
data/
  schema.sql      Ecommerce schema (Postgres-friendly DDL)
scripts/
  init_db.py      Creates + seeds the database (deterministic, seed=42)
```

**The loop** (in `agent.py`): send messages + tool schemas to the model → if it
requests tools, run each (parallel tool calls supported), append the results,
and loop → when it returns plain text, that's the answer. A `max_steps` guard
bounds each turn.

**Adding a tool** is one function: create `app/tools/mytool.py` with a
`register(registry, config)` that adds a `Tool(name, description, parameters,
handler)`, then list the module in `app/tools/__init__.py`.

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env      # then edit .env — at minimum set OPENAI_API_KEY

# 3. Create and seed the database
python scripts/init_db.py            # add --force to recreate

# 4. Chat with the agent
python -m app
```

### Required / optional keys

- `OPENAI_API_KEY` — **required**.
- `TAVILY_API_KEY` — optional; without it the two search tools return a clear
  "not configured" message instead of failing.
- SMTP settings — optional; email defaults to `EMAIL_DRY_RUN=true`, so composed
  messages are shown for review rather than actually sent.

## Seed data (ecommerce domain)

`scripts/init_db.py` generates a small but realistic store, deterministically:

- **8** categories, **40** products (with cost + margin data)
- **24** customers with addresses
- **60** orders across realistic statuses, **~157** order line items
- **~52** payments and **~38** verified-purchase reviews

Because the RNG is seeded, every run produces the same data — good for demos and
reproducible testing.

## Example prompts

- "What are my top 5 products by revenue, and what's the total?"
- "Which products are low on stock (under 60 units)?"
- "What's the average review rating for the Electronics category?"
- "Research current market prices for wireless earbuds and compare to my Aurora Earbuds Pro."
- "Draft a restock reminder email to myself and save it to a file."

## CLI commands

`/reset` clear history · `/tools` list tools · `/help` help · `/exit` quit.

## Safety notes

- The database tool is **read-only by default**; enable writes with
  `DB_ALLOW_WRITES=true`. It rejects multi-statement input and non-SELECT verbs.
- The file system tool is **sandboxed** to `WORKSPACE_DIR` — path traversal is
  blocked.
- Email is **dry-run by default**; set `EMAIL_DRY_RUN=false` to send for real.

## Moving to Postgres later

The DB tool's contract (`db_get_schema` / `db_run_sql`) is backend-agnostic.
To switch, replace `_connect()` in `app/tools/database.py` with a `psycopg`
connection and point `schema.sql` at Postgres (the DDL is written to port with
minimal changes). Nothing in the agent loop or other tools changes.
