# rnd-cb — Memory Chatbot

A full-stack chatbot with user authentication and **both short-term and
long-term memory**, instrumented end-to-end with **Langfuse**.

- **Backend:** FastAPI + SQLAlchemy + SQLite
- **LLM:** OpenAI (chat + embeddings)
- **Frontend:** React (Vite) + React Router
- **Auth:** register / login with JWT (bcrypt-hashed passwords)
- **Observability:** Langfuse — every chat request is a trace tied to the
  user id and session id, with nested generations for the assistant reply,
  memory extraction, and embeddings.

## Memory model

| Type | What it is | Where it lives |
| --- | --- | --- |
| **Short-term** | The last *N* messages of the current session, replayed to the model so it follows the ongoing conversation. | `messages` table, windowed by `SHORT_TERM_WINDOW`. |
| **Long-term** | Durable facts about the user (name, preferences, goals…) extracted after each exchange and retrieved by semantic similarity into future prompts — across *all* sessions. | `memories` table with OpenAI embeddings; cosine-similarity retrieval (top-K = `LONG_TERM_TOP_K`). |

If embeddings are unavailable, long-term retrieval gracefully falls back to
the most recent memories.

## Project layout

```
backend/
  app/
    main.py          FastAPI app + CORS + startup
    config.py        Settings (.env)
    database.py      SQLAlchemy engine / session
    models.py        User, ChatSession, Message, Memory
    schemas.py       Pydantic request/response models
    auth.py          JWT + password hashing + current-user dependency
    llm.py           OpenAI client + Langfuse tracing helpers
    memory.py        Short-term window + long-term extract/retrieve
    routers/
      auth.py        /api/auth/register, /login, /me
      chat.py        /api/chat, /api/sessions, /api/memories
  requirements.txt
  .env.example
frontend/
  src/
    api.js           fetch wrapper (bearer token)
    context/AuthContext.jsx
    pages/Login.jsx, Register.jsx, Chat.jsx
```

## Running locally

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in OPENAI_API_KEY and Langfuse keys
uvicorn app.main:app --reload --port 8000
```

The SQLite database (`chatbot.db`) is created automatically on startup.
API docs are available at `http://localhost:8000/docs`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` to the
backend on port 8000, so no extra CORS config is needed in development.

## Configuration

All backend settings come from `backend/.env` (see `.env.example`):

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Required. OpenAI key for chat + embeddings. |
| `OPENAI_MODEL` | Chat model (default `gpt-4o-mini`). |
| `OPENAI_EMBEDDING_MODEL` | Embedding model for long-term memory. |
| `JWT_SECRET` | Secret for signing JWTs — set a strong random value. |
| `DATABASE_URL` | SQLAlchemy URL (default local SQLite). |
| `SHORT_TERM_WINDOW` | Messages kept as short-term memory. |
| `LONG_TERM_TOP_K` | Long-term memories injected per request. |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` | Langfuse tracing (optional; disabled if unset). |
| `FRONTEND_ORIGIN` | Allowed CORS origin for the SPA. |

## API summary

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/auth/register` | — | Create account, returns JWT. |
| POST | `/api/auth/login` | — | Log in (username or email), returns JWT. |
| GET | `/api/auth/me` | ✅ | Current user. |
| GET | `/api/sessions` | ✅ | List chat sessions. |
| POST | `/api/sessions` | ✅ | Create a session. |
| GET | `/api/sessions/{id}` | ✅ | Session with messages. |
| DELETE | `/api/sessions/{id}` | ✅ | Delete a session. |
| POST | `/api/chat` | ✅ | Send a message; returns reply + Langfuse `trace_id`. |
| GET | `/api/memories` | ✅ | List the user's long-term memories. |
