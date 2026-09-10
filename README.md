# AI Text Summarizer

A small full-stack app that turns long text into concise, useful summaries using
the **OpenAI API**. Built as a learning project for prompt engineering,
text processing, context windows, and structured output.

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
  (title, summary, key points, decisions, action items, entities).
- **Token / context handling** — counts input tokens before sending, and for
  documents larger than a configurable threshold it automatically switches to a
  **chunked map-reduce** pass so arbitrarily long inputs still work.

## How it works

```
Browser (public/)  ──POST /api/summarize──▶  Express server (src/server.ts)
      ▲                                              │
      │  NDJSON stream of events                     ▼
      └──────────────────────────────  summarizeStreaming (src/summarizer.ts)
                                                     │
                          ┌──────────────────────────┴───────────────────────┐
                          │ input ≤ threshold          input > threshold       │
                          ▼                            ▼                        │
                    single streamed request     MAP: summarize each chunk      │
                                                 REDUCE: stream final summary   │
                          └──────────────── OpenAI API (src/openai.ts) ────────┘
```

Key modules:

| File | Responsibility |
|---|---|
| `src/prompts.ts` | Prompt engineering — composable length/style/format instructions. |
| `src/chunking.ts` | Splitting large text on paragraph/sentence boundaries. |
| `src/summarizer.ts` | Orchestration: single-pass vs. map-reduce, streaming, structured outputs. |
| `src/openai.ts` | Shared OpenAI client + local token counting (tiktoken). |
| `src/server.ts` | Express routes and the NDJSON streaming endpoint. |
| `public/` | Dependency-free web UI. |

## Setup

Requires Node.js 20+.

```bash
npm install
cp .env.example .env   # then add your OpenAI API key
npm run dev            # http://localhost:3000
```

The OpenAI SDK reads `OPENAI_API_KEY` from the environment. Set `OPENAI_BASE_URL`
to target an OpenAI-compatible endpoint (Azure OpenAI, a proxy, etc.).

### Scripts

- `npm run dev` — start with auto-reload (tsx).
- `npm run build` — compile TypeScript to `dist/`.
- `npm start` — run the compiled server.
- `npm run typecheck` — type-check without emitting.

## Configuration

Set in `.env` (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `3000` | Web server port. |
| `OPENAI_API_KEY` | — | Your OpenAI API key (required). |
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

### Streaming event types (NDJSON)

Each line of `/api/summarize` is one JSON object:

- `{ "type": "status", "message": "…" }` — progress updates.
- `{ "type": "meta", "inputTokens": N, "strategy": "single-pass" | "map-reduce", "chunks"?: N }`
- `{ "type": "delta", "text": "…" }` — a chunk of summary text.
- `{ "type": "done", "outputTokens": N, "inputTokens": N }`
- `{ "type": "error", "message": "…" }`
