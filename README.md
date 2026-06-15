# ContentForge — Multi-Agent AI Content Studio

A full-stack application that helps content writers generate **LinkedIn posts, website
articles, and blog posts** using a **multi-agent system**. Writers choose a tone, length,
platform, and audience; the system researches a trending topic from the last 24 hours,
writes the piece, verifies it, and returns a **Title, body, meta description, keywords,
hashtags — and the sources** used.

**Stack:** Python · FastAPI · PostgreSQL · OpenAI · React (Vite)

---

## How the multi-agent system works

The backend orchestrates three specialized agents (`backend/app/agents/`). Progress is
streamed live to the UI as newline-delimited JSON so the writer can watch each agent work.

| # | Agent | Role |
|---|-------|------|
| 1 | **Trend Researcher** (`trend_researcher.py`) | Does a **deep web search** (Tavily) restricted to the last ~24 hours based on the user's topic/audience, picks the most timely angle, then runs follow-up searches to collect **citable sources**. |
| 2 | **Content Writer** (`content_writer.py`) | Writes the title, body, meta description, SEO keywords and hashtags, grounded in the research and tailored to the chosen platform/tone/length. |
| 3 | **Verifier** (`verifier.py`) | Fact-checks the draft against the sources, scores quality, flags issues, and returns a polished final version. |

The **orchestrator** (`orchestrator.py`) runs them in sequence and emits events
(`agent_start`, `agent_complete`, `sources`, `complete`). Results are persisted to Postgres.

```
User → React UI → FastAPI /api/generate/stream → Orchestrator
                                                    ├─ 1. Trend Researcher → web_search (deep) → sources
                                                    ├─ 2. Content Writer   → title/body/keywords/hashtags
                                                    └─ 3. Verifier         → fact-check + polish
                                                  → PostgreSQL (saved) → streamed back to UI
```

> **Demo mode:** Without an `OPENAI_API_KEY` the pipeline still runs end-to-end with
> placeholder content/sources, so you can explore the UI before adding keys. Add
> `TAVILY_API_KEY` for real, citable sources from the last 24 hours.

---

## Quick start (Docker)

```bash
cp .env.example .env        # add your OPENAI_API_KEY (and optional TAVILY_API_KEY)
docker compose up --build
```

- Frontend: http://localhost:5173
- API + docs: http://localhost:8000/docs

## Run locally (without Docker)

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # set DATABASE_URL + OPENAI_API_KEY
uvicorn app.main:app --reload
```
Requires a PostgreSQL instance matching `DATABASE_URL`.

**Frontend**
```bash
cd frontend
npm install
npm run dev                  # proxies /api → http://localhost:8000
```

---

## Configuration

Backend env vars (`backend/.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/contentforge` | Async Postgres URL |
| `OPENAI_API_KEY` | — | Required for real generation |
| `OPENAI_MODEL` | `gpt-4o` | Writer/verifier model |
| `OPENAI_RESEARCH_MODEL` | `gpt-4o-mini` | Trend research model |
| `TAVILY_API_KEY` | — | Optional, enables real deep web search |
| `CORS_ORIGINS` | `*` | Allowed origins |

---

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/health` | Service + key status |
| `POST` | `/api/generate/stream` | Run the pipeline, stream NDJSON progress + result |
| `POST` | `/api/generate` | Run the pipeline, return the saved record (non-streaming) |
| `GET`  | `/api/content` | List previously generated content |
| `GET`  | `/api/content/{id}` | Fetch a single generated piece |

**Request body**
```json
{
  "topic": "AI in healthcare",
  "platform": "linkedin",          // linkedin | website | blog
  "tone": "professional",          // professional | casual | friendly | authoritative | inspirational | witty
  "length": "medium",              // short | medium | long
  "audience": "startup founders",
  "preferences": "include a real-world example"
}
```

---

## Project structure

```
backend/
  app/
    main.py              FastAPI app + lifespan
    config.py            Settings (env)
    database.py          Async SQLAlchemy engine/session
    models.py            ContentPiece ORM model
    schemas.py           Pydantic request/response models
    agents/
      orchestrator.py    Runs the 3-agent pipeline, emits events
      trend_researcher.py
      content_writer.py
      verifier.py
      base.py            Shared OpenAI client + JSON completion helper
      tools/web_search.py  Deep search (Tavily + offline fallback)
    api/routes.py        HTTP + streaming endpoints
    services/content_service.py  Persistence
frontend/
  src/
    App.jsx              State + stream consumption
    lib/api.js           NDJSON stream client
    components/          GenerateForm, AgentProgress, ResultView, Sources
    styles.css           Responsive modern theme
docker-compose.yml
```
