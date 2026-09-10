# AI Text Summarizer

A small full-stack app that turns long text into concise, useful summaries using
the Anthropic **Claude API**. Built as a learning project for prompt engineering,
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
                          └──────────────── Claude API (src/anthropic.ts) ─────┘
```

Key modules:

| File | Responsibility |
|---|---|
| `src/prompts.ts` | Prompt engineering — composable length/style/format instructions. |
| `src/chunking.ts` | Splitting large text on paragraph/sentence boundaries. |
| `src/summarizer.ts` | Orchestration: single-pass vs. map-reduce, streaming, JSON extraction. |
| `src/anthropic.ts` | Shared Claude client + token counting. |
| `src/server.ts` | Express routes and the NDJSON streaming endpoint. |
| `public/` | Dependency-free web UI. |

## Setup

Requires Node.js 20+.

```bash
npm install
cp .env.example .env   # then add your key, or use `ant auth login`
npm run dev            # http://localhost:3000
```

The Anthropic SDK resolves credentials from `ANTHROPIC_API_KEY`,
`ANTHROPIC_AUTH_TOKEN`, or an `ant auth login` profile — set whichever you use.

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
| `SUMMARIZER_MODEL` | `claude-opus-5` | Model to use. Try `claude-sonnet-5` / `claude-haiku-4-5` to trade quality for cost. |
| `CHUNK_THRESHOLD_TOKENS` | `180000` | Above this many input tokens, switch to map-reduce. Lower it to see chunking engage on smaller documents. |

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
