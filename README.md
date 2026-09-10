# 🧠 AI SQL Generator

Convert natural-language questions into **read-only SQL** — with automatic
explanation, formatting, and validation — powered by FastAPI, React, and the
OpenAI API.

> **Read-only by design.** Every generated (or submitted) query is parsed and
> checked; anything that could modify data or schema (`INSERT`, `UPDATE`,
> `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `GRANT`, …) is rejected.
> This is the safe foundation for the later *Deterministic SQL Data Analyst*
> project.

## Example

**You ask:**

> Show the top 10 customers by revenue.

**You get:**

```sql
SELECT
  customer_id,
  SUM(revenue) AS total_revenue
FROM sales
GROUP BY
  customer_id
ORDER BY
  total_revenue DESC
LIMIT 10
```

...plus a plain-language explanation, validation badges, and a saved history entry.

## Features

| Feature | Description |
| --- | --- |
| **Schema input** | Paste DDL or describe your tables; the model grounds SQL in your schema. |
| **Natural-language question** | Ask in plain English, choose a SQL dialect. |
| **SQL generation** | Structured (JSON) output from the LLM → predictable, single-statement SQL. |
| **SQL explanation** | Plain-language walkthrough of what a query does. |
| **SQL formatting** | Pretty-printed via `sqlglot` (dialect-aware) with a `sqlparse` fallback. |
| **Query validation** | Parses the SQL and enforces read-only; reports errors + advisory warnings. |
| **Query history** | Every generation is saved to SQLite; browse, reload, or delete past queries. |

## Architecture

```
ai-sql-generator/
├── setup.sh                # one-time setup (venv, deps, .env)
├── start.sh                # run backend + frontend together
├── backend/                # FastAPI + OpenAI
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py         # app + CORS + routers
│       ├── config.py       # settings from .env
│       ├── schemas.py      # Pydantic request/response models
│       ├── deps.py         # shared singletons
│       ├── routers/
│       │   ├── sql.py      # /generate /explain /format /validate
│       │   └── history.py  # /history CRUD
│       └── services/
│           ├── llm.py      # OpenAI text-to-SQL (structured output)
│           ├── sql_tools.py# formatting + read-only validation
│           └── history.py  # SQLite persistence
└── frontend/               # React + Vite
    └── src/
        ├── App.jsx
        ├── api/client.js
        └── components/
```

## Prerequisites

- **Python 3.12**
- **Node.js 18+** (20 or 22 recommended)
- An **OpenAI API key**

## Setup

```bash
./setup.sh
```

This creates `backend/.venv` (Python 3.12 virtual environment), installs backend
and frontend dependencies, and copies `backend/.env.example` → `backend/.env`.

> If `python3.12` is not on your `PATH`, point the script at it:
> `PYTHON_BIN=/path/to/python3.12 ./setup.sh`

Then add your OpenAI key to **`backend/.env`**:

```dotenv
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
SQL_DIALECT=postgres
```

## Run

```bash
./start.sh
```

- Frontend → <http://localhost:5173>
- Backend health → <http://localhost:8000/api/health>
- Interactive API docs → <http://localhost:8000/docs>

The Vite dev server proxies `/api` to the backend, so you only need the frontend
URL in your browser.

## API reference

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Service + LLM status |
| `POST` | `/api/generate` | `{question, schema_text, dialect}` → SQL + explanation + validation |
| `POST` | `/api/explain` | `{sql, schema_text, dialect}` → explanation |
| `POST` | `/api/format` | `{sql, dialect}` → formatted SQL |
| `POST` | `/api/validate` | `{sql, dialect}` → validation result |
| `GET` | `/api/history` | List saved queries |
| `GET` | `/api/history/{id}` | Fetch one saved query |
| `DELETE` | `/api/history/{id}` | Delete one saved query |
| `DELETE` | `/api/history` | Clear all history |

### Example: generate

```bash
curl -s http://localhost:8000/api/generate \
  -H 'Content-Type: application/json' \
  -d '{
        "question": "Show the top 10 customers by revenue.",
        "schema_text": "CREATE TABLE sales (customer_id INT, revenue NUMERIC);",
        "dialect": "postgres"
      }' | python -m json.tool
```

## Notes & roadmap

- Formatting and validation work **without** an API key — only `/generate` and
  `/explain` require OpenAI.
- History is stored in `backend/history.db` (SQLite, git-ignored).
- **Next step:** evolve into the *Deterministic SQL Data Analyst* — execute the
  validated read-only queries against a real database and return results.

## What you learn

Text-to-SQL, structured LLM output, SQL dialects & parsing, read-only safety
enforcement, and a clean FastAPI + React full-stack layout.
