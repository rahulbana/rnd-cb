# Production-style AI Chatbot

A full-stack, production-shaped AI chat application.

```
React UI  →  FastAPI  →  LLM (Claude)  →  Conversation Manager  →  SQLite
```

## Features

- **Chat interface** — clean, responsive React UI (light & dark).
- **Streaming responses** — tokens stream to the browser over Server-Sent Events.
- **Conversation history** — every message persisted in SQLite.
- **New conversation** — start fresh chats; titles auto-derived from the first message.
- **Delete conversation** — remove a chat and its messages.
- **System prompt** — per-conversation, editable in the settings panel.
- **Temperature / configuration** — per-conversation temperature, plus server-side model and effort configuration.
- **Error handling** — graceful failures on both the API and UI (rate limits, network, config).
- **Logging** — structured stdout logging across the backend.
- **Basic authentication** — HTTP Basic auth guards every API route.

## Architecture

| Layer | Responsibility | Files |
|-------|----------------|-------|
| **React UI** | Chat, sidebar, settings, streaming rendering | `frontend/src/` |
| **FastAPI** | REST + SSE endpoints, auth, CORS, error handling | `backend/app/main.py`, `auth.py` |
| **LLM** | Anthropic Claude client, streaming, temperature gating | `backend/app/llm.py` |
| **Conversation Manager** | History assembly + persistence | `backend/app/conversation.py` |
| **SQLite** | Durable storage of conversations & messages | `backend/app/database.py`, `models.py` |

## Prerequisites

- Python 3.11+
- Node.js 18+
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

## Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env         # then edit .env
# Set at minimum:
#   ANTHROPIC_API_KEY=sk-ant-...
#   AUTH_USERNAME=admin
#   AUTH_PASSWORD=<something secret>

uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`).

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` and sign in with the `AUTH_USERNAME` /
`AUTH_PASSWORD` you configured. The Vite dev server proxies `/api` to the
backend on port 8000 (configurable in `vite.config.js`).

To build for production: `npm run build` (outputs to `frontend/dist/`).

## Configuration

All backend settings are environment variables (see `backend/.env.example`):

| Variable | Default | Notes |
|----------|---------|-------|
| `ANTHROPIC_API_KEY` | — | Required to talk to the model. |
| `MODEL` | `claude-opus-5` | Any Claude model id. |
| `EFFORT` | `medium` | Thinking depth / token spend: `low`…`max`. |
| `MAX_TOKENS` | `4096` | Max tokens per reply. |
| `DEFAULT_SYSTEM_PROMPT` | helpful assistant | Applied to new conversations. |
| `DEFAULT_TEMPERATURE` | `1.0` | Applied to new conversations. |
| `AUTH_USERNAME` / `AUTH_PASSWORD` | `admin` / `changeme` | **Change these.** |
| `DATABASE_URL` | local SQLite file | Async SQLAlchemy URL. |
| `CORS_ORIGINS` | localhost:5173 | Comma-separated allowed origins. |
| `LOG_LEVEL` | `INFO` | Standard logging level. |

### A note on temperature

Current frontier Claude models (`claude-opus-5`, `claude-sonnet-5`,
`claude-opus-4-8`, …) **do not accept the `temperature` parameter** — they use
the `effort` setting instead. The app stores a per-conversation temperature and
exposes it in the UI, but only sends it to models that support sampling
(e.g. `claude-haiku-4-5`, `claude-sonnet-4-6`). When the active model doesn't
support it, the settings panel shows a note and the value is saved but not
applied. Set `MODEL=claude-haiku-4-5` to make temperature take effect.

## API reference

All routes require HTTP Basic auth.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Liveness check (no auth). |
| `GET` | `/api/me` | Verify credentials; report model & capabilities. |
| `GET` | `/api/conversations` | List conversations (newest first). |
| `POST` | `/api/conversations` | Create a conversation. |
| `GET` | `/api/conversations/{id}` | Get a conversation with messages. |
| `PATCH` | `/api/conversations/{id}` | Update title / system prompt / temperature. |
| `DELETE` | `/api/conversations/{id}` | Delete a conversation. |
| `POST` | `/api/conversations/{id}/messages` | Send a message; stream reply (SSE). |

The streaming endpoint returns `text/event-stream`. Each frame is JSON:

```
data: {"type": "delta", "text": "Hello"}
data: {"type": "done", "message_id": "…"}
data: {"type": "error", "detail": "…"}
```

## Project layout

```
backend/
  app/
    main.py            # FastAPI app, routes, SSE streaming
    config.py          # Settings (pydantic-settings)
    logging_config.py  # Structured logging
    database.py        # Async SQLAlchemy engine/session
    models.py          # Conversation, Message ORM models
    schemas.py         # Pydantic request/response models
    auth.py            # HTTP Basic auth
    llm.py             # Anthropic client + streaming + temp gating
    conversation.py    # Conversation Manager (persistence)
  requirements.txt
  .env.example
frontend/
  src/
    App.jsx            # State orchestration
    api.js             # API client + SSE parsing
    components/        # Login, Sidebar, ChatWindow, Composer, SettingsPanel, MessageBubble
    styles.css
  package.json
  vite.config.js
  .env.example
```
