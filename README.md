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
- 🎨 **Writing-style references** — in Settings, add links or upload .txt/.md/
  .docx samples of your previous writing. They're embedded into a dedicated
  index, and the most relevant samples are fed into every generation so the AI
  writes in *your* voice.
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
- 🖼️ **AI banner images** — generate a title-aware hero image for any article
  with one click; it sits on top of the content, shows on library cards, and is
  embedded into PDF/DOCX/Markdown exports.
- 📤 **Export** — download any article as PDF, DOCX or Markdown.
- 🌗 Modern, responsive UI (Mantine) with light/dark mode.
- 📊 **LLM observability (Langfuse)** — every generation/expand/banner request
  is traced end to end: the user's input, each model call, the tools that ran
  (RAG, style refs, web research, duplicate detection) as nested spans, and the
  output — grouped by **working session** and tagged by user. Captures quality
  signals too: an explicit **thumbs up/down** on each draft and an automatic
  **edit-retention** score (how close the saved article stays to the AI draft).
  Activates automatically when Langfuse keys are set; a no-op otherwise.

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
| `LANGFUSE_PUBLIC_KEY`| _(none)_                         | Enables LLM tracing when set (with secret) |
| `LANGFUSE_SECRET_KEY`| _(none)_                         | Langfuse secret key                        |
| `LANGFUSE_HOST`      | `https://cloud.langfuse.com`     | Langfuse endpoint (cloud or self-hosted)   |
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
| POST   | `/articles/{id}/banner`       | Generate a banner image         |
| POST   | `/generate`                   | AI-generate content + metadata  |
| POST   | `/generate/expand`            | Expand/lengthen an article body |
| GET    | `/search?q=`                  | Semantic search                 |
| GET    | `/articles/{id}/export?format=` | Export pdf \| docx \| md      |
| GET    | `/style-references`           | List writing-style references   |
| POST   | `/style-references/link`      | Add a style reference by URL    |
| POST   | `/style-references/upload`    | Upload a .txt/.md/.docx sample  |
| DELETE | `/style-references/{id}`      | Remove a style reference        |

---

## Observability (Langfuse)

Set `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` (from
[Langfuse Cloud](https://cloud.langfuse.com) or a self-hosted instance) and
tracing switches on automatically — no code changes, and it's a no-op when
the keys are absent.

**One trace per request.** An ASGI middleware wraps every API call in a single
trace, so you can observe a user's whole request → response in one place:

- the **full request payload** as the trace input and the **full response**
  as the output (secrets like passwords/tokens are redacted, bodies size-capped;
  large uploads and file downloads are skipped);
- nested underneath, the **OpenAI calls** (query planning, generation,
  expansion, embeddings, image) with token usage and latency, plus a
  **span for each tool** that ran — `retrieve.rag`,
  `retrieve.style_references`, `research.web`, `detect.duplicates`,
  `image.banner`;
- **`user_id`**, **session id** and **tags** (the tools used), so you can
  filter and aggregate per user, per session and per capability.

Set `LANGFUSE_TRACE_REQUESTS=false` to trace only the LLM calls instead of
every request.

**Sessions & scores**

- Each browser working session sends an `X-Session-Id` header, so a writer's
  multiple generations, expands and banners group into one Langfuse **session**.
- **Explicit feedback:** thumbs up/down on a generated draft posts to
  `POST /generate/feedback`, recording a `user_rating` score on that trace.
- **Implicit feedback:** when a generated article is saved, the backend scores
  `edit_retention` — the similarity between the saved body and the original AI
  draft (1.0 = kept as-is, lower = heavily rewritten) — so you can see which
  prompts/settings produce drafts writers keep.

Check `GET /health` — `"tracing": true` confirms it's active.

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
