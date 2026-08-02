# 🎬 Reel — Movie Concierge

A full-stack AI assistant that answers questions about movies, translates text,
and does world-time math — built on **OpenAI**, **LangGraph**, **FastAPI**, and
**React**, with all of its capabilities served from a **remote MCP server**.

The MCP server is the interesting bit: rather than hard-coding tools into the
agent, the backend connects to a standalone [Model Context
Protocol](https://modelcontextprotocol.io) server over the network, discovers
its tools at runtime, and hands them to a LangGraph ReAct agent. Swap or extend
the MCP server and the agent picks up the new tools with no code changes.

```
┌─────────────┐     HTTP/SSE      ┌──────────────────────┐   streamable-HTTP   ┌────────────────────┐
│   React UI  │ ◀───────────────▶ │  FastAPI + LangGraph │ ◀─────────(MCP)───▶ │  Remote MCP server │
│  (Vite/TS)  │   /api/chat/stream│   ReAct agent (OpenAI)│    tool discovery   │  TMDB · translate  │
└─────────────┘                   └──────────────────────┘   + invocation      │  · world-time      │
                                                                                └─────────┬──────────┘
                                                                                          │ REST
                                                                                    ┌─────▼──────┐
                                                                                    │    TMDB    │
                                                                                    └────────────┘
```

## Features

- **Streaming chat** — assistant tokens stream to the browser over SSE, with
  live "tool call" chips so you can see the agent search TMDB or translate text
  in real time.
- **TMDB tools** — search movies, full movie details (cast, director, trailers),
  trending, genre-aware discovery, and people search.
- **Utility tools** — language translation (auto source detection) and
  world-time helpers (current time, timezone comparison, time conversion).
- **Remote MCP architecture** — tools live in a separate, independently
  deployable server and are consumed via `langchain-mcp-adapters`.

## Project layout

```
mcp_server/    Remote MCP server (FastMCP, streamable-HTTP)
  app/
    server.py      Tool registrations + transport
    tmdb.py        Async TMDB REST client
    translation.py Google-Translate-backed translator
    timetools.py   zoneinfo-based world-time helpers
backend/       FastAPI + LangGraph agent (MCP client)
  app/
    main.py        API + SSE streaming endpoint
    agent.py       MCP tool loading + create_react_agent
    config.py      Settings (OpenAI, MCP URL, CORS)
frontend/      React + Vite + TypeScript chat UI
docker-compose.yml
```

## Prerequisites

- Python 3.11+
- Node 18+
- An **OpenAI API key** ([platform.openai.com](https://platform.openai.com))
- A **TMDB API key / read token** (free — [themoviedb.org](https://www.themoviedb.org/settings/api))

## Quick start (local)

Open three terminals.

**1. Remote MCP server**
```bash
cd mcp_server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add MCP_TMDB_READ_ACCESS_TOKEN
python -m app.server        # serves http://localhost:8100/mcp
```

**2. Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

**3. Frontend**
```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

Open http://localhost:5173 and start chatting.

> The `Makefile` wraps these: `make install-mcp install-backend install-frontend`,
> then `make mcp`, `make backend`, `make frontend`.

## Quick start (Docker)

```bash
cp .env.example .env        # add OPENAI_API_KEY and a TMDB token
docker compose up --build
```

- Frontend → http://localhost:8080
- Backend  → http://localhost:8000
- MCP server → http://localhost:8100/mcp

## Configuration

| Service | Variable | Purpose |
| --- | --- | --- |
| MCP | `MCP_TMDB_READ_ACCESS_TOKEN` / `MCP_TMDB_API_KEY` | TMDB auth (one required) |
| MCP | `MCP_HOST`, `MCP_PORT` | Bind address for the transport |
| Backend | `OPENAI_API_KEY` | OpenAI auth |
| Backend | `OPENAI_MODEL` | Chat model (default `gpt-4o-mini`) |
| Backend | `MCP_SERVER_URL` | Remote MCP endpoint |
| Backend | `CORS_ALLOW_ORIGINS` | JSON array of allowed origins |

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Status, model, and discovered tool names |
| `POST` | `/api/chat/stream` | SSE stream of the assistant reply |

`/api/chat/stream` accepts `{"messages": [{"role": "user", "content": "..."}]}`
and emits SSE frames: `start`, `token`, `tool_call`, `tool_result`, `done`,
`error`.

## Extending the tools

Add a function to the MCP server and decorate it with `@mcp.tool()`; its
docstring becomes the description the LLM reads. Restart the MCP server and the
backend rediscovers it on next startup — no agent code changes needed.

```python
@mcp.tool()
def now_playing(region: str = "US") -> dict:
    """List movies currently in theaters for a region."""
    ...
```
