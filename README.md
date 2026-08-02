# 🎬 Reel — Movie Concierge

A full-stack AI assistant that answers questions about movies, translates text,
and does world-time math — built on **OpenAI**, **LangGraph**, **FastAPI**, and
**React**.

The agent draws its tools from **two sources at once**:

- **A remote MCP server** provides the **movie (TMDB)** tools. Rather than
  hard-coding them, the backend connects to a standalone [Model Context
  Protocol](https://modelcontextprotocol.io) server over the network and
  discovers its tools at runtime — swap or extend that server and the agent
  picks up the changes with no code edits.
- **Native application tools** provide **translation** and **world-time**. These
  live inside the backend and are registered directly with the same LangGraph
  agent.

```
┌─────────────┐   HTTP/SSE    ┌──────────────────────────────┐  streamable-HTTP  ┌────────────────────┐
│   React UI  │ ◀───────────▶ │  FastAPI + LangGraph agent    │ ◀──────(MCP)────▶ │  Remote MCP server │
│  (Vite/TS)  │ /api/chat/... │  (OpenAI ReAct)               │  movie tools only │      (TMDB)        │
└─────────────┘               │                               │                   └─────────┬──────────┘
                              │  + native tools:              │                             │ REST
                              │    translate · world-time     │                       ┌─────▼──────┐
                              └──────────────────────────────┘                        │    TMDB    │
                                                                                       └────────────┘
```

## Features

- **Streaming chat** — assistant tokens stream to the browser over SSE, with
  live "tool call" chips so you can see the agent search TMDB or translate text
  in real time.
- **Movie tools (remote MCP)** — search movies, full movie details (cast,
  director, trailers), trending, genre-aware discovery, and people search.
- **Native app tools** — language translation (auto source detection) and
  world-time helpers (current time, timezone comparison, time conversion).
- **Hybrid tool wiring** — MCP-discovered tools and local tools are merged into
  one agent, so the model uses them interchangeably.

## Project layout

```
mcp_server/    Remote MCP server — movie tools only (FastMCP, streamable-HTTP)
  app/
    server.py      TMDB tool registrations + transport
    tmdb.py        Async TMDB REST client
backend/       FastAPI + LangGraph agent (MCP client + native tools)
  app/
    main.py        API + SSE streaming endpoint
    agent.py       Merges MCP movie tools with local tools; create_react_agent
    config.py      Settings (OpenAI, MCP URL, CORS)
    tools/         Native application tools
      translation.py  Google-Translate-backed translator
      timetools.py    zoneinfo-based world-time helpers
      __init__.py     LangChain @tool wrappers (LOCAL_TOOLS)
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

There are two places to add a tool, depending on where it belongs:

**1. A movie / external tool → the remote MCP server.** Add a function in
`mcp_server/app/server.py` decorated with `@mcp.tool()`; its docstring becomes
the description the LLM reads. Restart the MCP server and the backend
rediscovers it on next startup — no agent code changes needed.

```python
@mcp.tool()
async def now_playing(region: str = "US") -> dict:
    """List movies currently in theaters for a region."""
    ...
```

**2. A native application tool → the backend.** Add a `@tool` in
`backend/app/tools/` and include it in `LOCAL_TOOLS`. It is registered with the
agent alongside the MCP tools.

```python
@tool
def convert_currency(amount: float, base: str, quote: str) -> dict:
    """Convert an amount between two currencies."""
    ...
```
