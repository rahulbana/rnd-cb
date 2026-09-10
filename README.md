# AI Text Summarizer

A small full-stack app that turns long text into concise, useful summaries using
the **OpenAI API**. Built as a learning project for prompt engineering,
text processing, context windows, and structured output.

Backend: **Python + FastAPI**. Frontend: **React + TypeScript** (built with Vite).

## Features

- **Text input / upload** — paste text or upload a `.txt` / `.md` file.
- **Length control** — short, medium, or detailed summaries.
- **Summary styles** — neutral, executive, technical, academic, casual, or ELI5.
- **Formats** — flowing paragraph, bullet points, extracted key points, or a
  structured executive report (Executive Summary / Key Findings / Important
  Decisions / Action Items).
- **Focus steering** — an optional free-text instruction, e.g. "emphasize risks".
- **Streaming responses** — summaries stream token-by-token to the browser.
- **Structured extraction** — a separate endpoint returns machine-readable JSON
  (title, summary, key points, decisions, action items, entities) via OpenAI
  Structured Outputs.
- **Token / context handling** — counts input tokens before sending, and for
  documents larger than a configurable threshold it automatically switches to a
  **chunked map-reduce** pass so arbitrarily long inputs still work.

## How it works

```
Browser (public/)  ──POST /api/summarize──▶  FastAPI app (app/main.py)
      ▲                                              │
      │  NDJSON stream of events                     ▼
      └──────────────────────────────  summarize_streaming (app/summarizer.py)
                                                     │
                          ┌──────────────────────────┴───────────────────────┐
                          │ input ≤ threshold          input > threshold       │
                          ▼                            ▼                        │
                    single streamed request     MAP: summarize each chunk      │
                                                 REDUCE: stream final summary   │
                          └──────────────── OpenAI API (app/llm.py) ───────────┘
```

Key modules:

| File | Responsibility |
|---|---|
| `app/prompts.py` | Prompt engineering — composable length/style/format instructions. |
| `app/chunking.py` | Splitting large text on paragraph/sentence boundaries. |
| `app/summarizer.py` | Orchestration: single-pass vs. map-reduce, streaming, structured outputs. |
| `app/llm.py` | Shared OpenAI client + local token counting (tiktoken, with a fallback). |
| `app/models.py` | Pydantic request/response schemas and the option vocabulary. |
| `app/main.py` | FastAPI routes, the NDJSON streaming endpoint, and static hosting. |
| `frontend/` | React + TypeScript UI (Vite). Builds into `public/`. |

### Frontend (`frontend/`)

| File | Responsibility |
|---|---|
| `src/App.tsx` | Top-level state and orchestration. |
| `src/api.ts` | `fetch` helpers + NDJSON stream reader. |
| `src/components/InputPanel.tsx` | Text input, upload, controls, actions. |
| `src/components/OutputPanel.tsx` | Streaming markdown (react-markdown) and structured results. |

## Quick start

Requires Python 3.11+ and Node.js 20+.

```bash
./setup.sh              # install deps + build the frontend + create .env
# edit .env and set OPENAI_API_KEY
./start.sh              # serve on http://localhost:3000
# ./start.sh --reload   # dev mode with auto-reload
```

The manual steps below are equivalent.

## Setup (manual)

**1. Build the frontend** (outputs to `public/`, which the backend serves):

```bash
cd frontend
npm install
npm run build
cd ..
```

**2. Run the backend:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then add your OpenAI API key

uvicorn app.main:app --reload --port 3000
# → http://localhost:3000
```

The OpenAI SDK reads `OPENAI_API_KEY` from the environment. Set `OPENAI_BASE_URL`
to target an OpenAI-compatible endpoint (Azure OpenAI, a proxy, etc.).

> If you open the app before building the frontend, the server returns a short
> "build the frontend" page; the `/api/*` endpoints work regardless.

### Frontend development (hot reload)

Run the backend and the Vite dev server side by side. Vite proxies `/api` to the
backend, so you get instant reloads on the UI:

```bash
# terminal 1 — backend
uvicorn app.main:app --reload --port 3000

# terminal 2 — frontend dev server (http://localhost:5173)
cd frontend && npm run dev
```

> Token counting uses `tiktoken`, which downloads its encoding data on first use.
> If that download is blocked (offline / restricted network), the app falls back
> to a character-based estimate automatically.

## Configuration

Set in `.env` (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `3000` | Web server port (passed to uvicorn). |
| `OPENAI_API_KEY` | — | Your OpenAI API key (required for summaries). |
| `OPENAI_BASE_URL` | OpenAI default | Optional OpenAI-compatible endpoint. |
| `SUMMARIZER_MODEL` | `gpt-4o-mini` | Model to use. Try `gpt-4o` / `gpt-4.1` for higher quality. |
| `CHUNK_THRESHOLD_TOKENS` | `100000` | Above this many input tokens, switch to map-reduce. Lower it to see chunking engage on smaller documents. |

## API

| Endpoint | Method | Body | Response |
|---|---|---|---|
| `/api/config` | GET | — | Model + available option values. |
| `/api/count-tokens` | POST | `{ text, length, style, format, focus? }` | `{ inputTokens, model }` |
| `/api/summarize` | POST | `{ text, length, style, format, focus? }` | NDJSON stream of events |
| `/api/extract` | POST | `{ text }` | Structured summary JSON |

Errors return `{ "error": "…" }` with an appropriate status code.

### Streaming event types (NDJSON)

Each line of `/api/summarize` is one JSON object:

- `{ "type": "status", "message": "…" }` — progress updates.
- `{ "type": "meta", "inputTokens": N, "strategy": "single-pass" | "map-reduce", "chunks"?: N }`
- `{ "type": "delta", "text": "…" }` — a chunk of summary text.
- `{ "type": "done", "outputTokens": N, "inputTokens": N }`
- `{ "type": "error", "message": "…" }`
