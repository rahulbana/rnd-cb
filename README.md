# AI Content Writer

A full-stack web application that helps content writers produce and manage
articles with AI. Describe what you want to write, and the app generates the
**title, body, summary, SEO description, SEO keywords, sentiment, tags, NER
tags and sources/references** — every field editable before and after saving. Your whole content
library is searchable semantically and exportable to PDF, Word and Markdown.

---

## Features

- 🔐 **Multi-user auth** — JWT-based register / login; each writer sees only
  their own content.
- ✨ **AI generation** — one brief → full article + rich metadata via OpenAI
  structured outputs.
- 📝 **Fully editable** — a WYSIWYG (Markdown-backed) body editor plus editable
  title, summary, SEO fields, sentiment, tags and named entities. Edit any time
  after saving.
- ➕ **Long-form + Expand** — pick a length up to a 3000+ word deep-dive, and
  expand any existing article on demand (lengthen, add examples, deepen
  sections, or append an FAQ) with a live word count.
- 🔎 **Semantic search** — find past articles by meaning, powered by ChromaDB +
  embeddings.
- 🧠 **RAG style context** — generation retrieves your similar past articles so
  new content matches your voice.
- 🌐 **Deep web research** — optionally search the live web before writing: the
  app plans multiple focused queries, searches, grounds the article in what it
  finds, and records the **real, verifiable source URLs**. Uses OpenAI's
  built-in web search by default (no extra key); Tavily supported as an option.
- 🪞 **Duplicate detection** — warns when new content is very similar to
  something you already wrote.
- 🔗 **Sources & references** — every article stores where its content came
  from: the writer's own past articles used as RAG context (tracked reliably),
  plus any external references the model cites. Editable, and included in
  exports.
- 📤 **Export** — download any article as PDF, DOCX or Markdown.
- 🌗 Modern, responsive UI (Mantine) with light/dark mode.

## Tech stack

| Layer      | Technology                                                        |
| ---------- | ----------------------------------------------------------------- |
| Frontend   | React + TypeScript, Vite, Mantine UI, TanStack Query, TipTap      |
| Backend    | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2                      |
| Database   | PostgreSQL (SQLite fallback for local dev)                        |
| Vector DB  | ChromaDB (in-memory fallback)                                     |
| LLM        | OpenAI (configurable model)                                       |
| Embeddings | Pluggable: `hash` (default) · `sentence_transformers` · `openai`  |
| Export     | reportlab (PDF), python-docx (DOCX), Markdown                     |

> **Embeddings note:** the spec's `BAAI/bge-m3` is a ~2 GB local model. The app
> ships with a zero-dependency `hash` embedder so it runs anywhere out of the
> box, and a lightweight `all-MiniLM-L6-v2` default for real semantic quality.
> To use bge-m3 in production: `pip install sentence-transformers` and set
> `EMBEDDING_PROVIDER=sentence_transformers`, `EMBEDDING_MODEL=BAAI/bge-m3`.

---

## Quick start (Docker)

```bash
# from the repo root
export OPENAI_API_KEY=sk-...        # optional; generation is disabled without it
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
docker compose up --build
```

- Frontend → http://localhost:8080
- Backend API docs → http://localhost:8000/docs

## Local development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit: set OPENAI_API_KEY, SECRET_KEY
uvicorn app.main:app --reload
```

Runs on http://localhost:8000 (SQLite by default — no database setup needed).
Interactive API docs at `/docs`.

Run the end-to-end smoke test (no external services required):

```bash
cd backend && PYTHONPATH=. python tests/smoke_test.py
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env           # optional
npm run dev
```

Runs on http://localhost:5173 and proxies `/api` to the backend at
`http://localhost:8000`.

---

## Configuration

All backend settings are environment variables (see `backend/.env.example`).
Key ones:

| Variable             | Default                          | Purpose                                    |
| -------------------- | -------------------------------- | ------------------------------------------ |
| `DATABASE_URL`       | `sqlite+aiosqlite:///...`        | Postgres in prod, SQLite for local dev     |
| `SECRET_KEY`         | dev placeholder                  | **Change in production** (JWT signing)     |
| `OPENAI_API_KEY`     | _(none)_                         | Enables AI generation                      |
| `LLM_MODEL`          | `gpt-4o-mini`                    | OpenAI chat model                          |
| `EMBEDDING_PROVIDER` | `hash`                           | `hash` · `sentence_transformers` · `openai`|
| `WEB_SEARCH_PROVIDER`| `openai`                         | `openai` · `tavily` · `none`               |
| `TAVILY_API_KEY`     | _(none)_                         | Required only for the `tavily` provider    |
| `CHROMA_PERSIST_DIR` | `./chroma_data`                  | ChromaDB persistence path                  |

## API overview

Base path: `/api/v1`

| Method | Path                          | Description                     |
| ------ | ----------------------------- | ------------------------------- |
| POST   | `/auth/register`              | Create account, returns token   |
| POST   | `/auth/login`                 | Login (OAuth2 form), returns token |
| GET    | `/auth/me`                    | Current user                    |
| GET    | `/articles`                   | List my articles                |
| POST   | `/articles`                   | Create article                  |
| GET    | `/articles/{id}`              | Get one                         |
| PATCH  | `/articles/{id}`              | Partial update (edit any field) |
| DELETE | `/articles/{id}`              | Delete                          |
| POST   | `/generate`                   | AI-generate content + metadata  |
| POST   | `/generate/expand`            | Expand/lengthen an article body |
| GET    | `/search?q=`                  | Semantic search                 |
| GET    | `/articles/{id}/export?format=` | Export pdf \| docx \| md      |

---

## Project structure

```
backend/
  app/
    core/        config, async DB, security (JWT + bcrypt)
    models/      SQLAlchemy models (User, Article)
    schemas/     Pydantic request/response models
    services/    llm, embeddings, vectorstore, export
    api/routes/  auth, articles, generation, search, export
  tests/smoke_test.py
frontend/
  src/
    api/         axios client + typed endpoints
    auth/        auth context + protected routes
    components/  layout, WYSIWYG editor, NER editor, badges
    pages/       login, register, dashboard, generate, editor
```

## Roadmap / next steps

- Alembic migrations (currently `create_all` on startup)
- Streaming generation (SSE) for a live typewriter effect
- Article versioning / revision history
- Refresh-token rotation
- Per-request rate limiting
