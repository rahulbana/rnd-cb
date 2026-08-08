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
| **Email — send** (`send_email`) | Send email over SMTP, with a dry-run mode. |
| **Email — read** (`search_emails`, `read_email`) | Search and read a mailbox over IMAP (read-only; never marks messages seen). |
| **Calculator** (`calculator`) | Safe, exact arithmetic (AST-based, no `eval`). |
| **Shell** (`run_shell`) | Run shell commands. **Disabled by default** — opt in with `SHELL_TOOL_ENABLED=true`. Timeout + bounded output. |

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
    email_tool.py SMTP send + IMAP read
    calculator.py AST-based safe evaluator
    shell.py      Shell command runner (opt-in, off by default)
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
- SMTP settings — optional; sending defaults to `EMAIL_DRY_RUN=true`, so
  composed messages are shown for review rather than actually sent.
- IMAP settings — optional; enable `search_emails` / `read_email`. Credentials
  default to the SMTP ones. Reading is always read-only.

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

### Shell tool prompts

The shell tool is **off by default** — set `SHELL_TOOL_ENABLED=true` in `.env`
first (see the safety note below). Then just describe the task in plain
English; the agent decides when to call `run_shell` and reads back the exit
code, stdout, and stderr.

System / file inspection:

- "Show me the disk usage of the current directory, biggest folders first."
- "How many Python files are in this project and how many lines total?"
- "Check whether `sqlite3` and `python3` are installed and print their versions."

Git / project:

- "Run git status and the last 5 commits, then summarize what changed recently."
- "Create a .venv, install requirements.txt into it, and tell me if anything failed."
- "Run the tests with `pytest -q`; if they fail, show me only the failing test names."

Combining shell with the other tools (where it shines):

- "Export my top 10 products by revenue to workspace/top_products.csv, then run
  `wc -l` on the file to confirm the row count."
- "Back up the database by copying data/ecommerce.db to
  workspace/backup_$(date +%F).db, then list the workspace to confirm."

Keeping it constrained — say so and the agent will comply:

- "Using the shell, show me what `find . -name \"*.db\"` returns — don't delete anything."
- "Run this exact command and just report the output: `uname -a && whoami`"

Commands run in a fixed working directory (the workspace sandbox unless
`SHELL_WORKDIR` is set) with a timeout (`SHELL_TIMEOUT`, default 30s).

## CLI commands

`/reset` clear history · `/tools` list tools · `/help` help · `/exit` quit.

## Safety notes

- The database tool is **read-only by default**; enable writes with
  `DB_ALLOW_WRITES=true`. It rejects multi-statement input and non-SELECT verbs.
- The file system tool is **sandboxed** to `WORKSPACE_DIR` — path traversal is
  blocked.
- Email is **dry-run by default**; set `EMAIL_DRY_RUN=false` to send for real.
- The shell tool is **disabled by default**; it only appears when
  `SHELL_TOOL_ENABLED=true`. It runs arbitrary commands with your privileges —
  enable it only in an environment you trust. Commands run in a fixed working
  directory with a timeout and bounded output.

## Moving to Postgres later

The DB tool's contract (`db_get_schema` / `db_run_sql`) is backend-agnostic.
To switch, replace `_connect()` in `app/tools/database.py` with a `psycopg`
connection and point `schema.sql` at Postgres (the DDL is written to port with
minimal changes). Nothing in the agent loop or other tools changes.
