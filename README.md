# rnd-cb — Agentic App (OpenAI + MCP + Tools)

An agentic application powered by an **OpenAI LLM** that combines three families of
capabilities:

1. **Remote MCP server** — a SQLite-backed *client directory* (name, country, state,
   city, contact number, email) exposed over the **streamable-HTTP** MCP transport.
2. **Web search tools** — Tavily (high quality, keyed) and DuckDuckGo (keyless fallback).
3. **Custom tools** — a live currency converter.

The agent is built on the **OpenAI Agents SDK**, which gives it native OpenAI LLM
support, function tools, and a first-class MCP client.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  agentic_app (OpenAI Agents SDK)                           │
│                                                            │
│   Agent (OpenAI LLM: gpt-4o)                               │
│    ├─ local function tools                                 │
│    │    ├─ web_search_tavily                               │
│    │    ├─ web_search_duckduckgo                           │
│    │    └─ convert_currency                                │
│    └─ MCP client (streamable-HTTP) ──────────┐             │
└──────────────────────────────────────────────┼────────────┘
                                                │ HTTP /mcp
┌───────────────────────────────────────────────▼───────────┐
│  mcp_server (FastMCP, remote)                              │
│   tools: add/get/list/search/update/delete/count clients  │
│   store: SQLite (mcp_server/db.py → clients.db)           │
└────────────────────────────────────────────────────────────┘
```

### Layout

```
├── mcp_server/               # Remote SQLite MCP server
│   ├── db.py                 #   CRUD + search storage layer
│   └── server.py             #   FastMCP tools + streamable-HTTP entrypoint
├── src/agentic_app/
│   ├── config.py             # pydantic-settings (single source of truth)
│   ├── agent.py              # builds the Agent (LLM + tools + MCP server)
│   ├── main.py               # CLI chat loop / single-shot query
│   └── tools/
│       ├── web_search.py     # Tavily + DuckDuckGo
│       └── currency.py       # currency converter
├── scripts/seed_clients.py   # seed sample clients
└── tests/test_db.py          # storage-layer unit tests
```

## Setup

Requires Python 3.10+.

```bash
# 1. Install (editable, with dev tools)
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env
#   → set OPENAI_API_KEY (required)
#   → optionally set TAVILY_API_KEY for higher-quality web search
```

Key environment variables (see `.env.example`):

| Var | Purpose | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | OpenAI auth (required) | — |
| `OPENAI_MODEL` | Chat model | `gpt-4o` |
| `MCP_SERVER_URL` | Where the agent connects | `http://localhost:8000/mcp` |
| `MCP_HOST` / `MCP_PORT` | Where the MCP server binds | `0.0.0.0` / `8000` |
| `MCP_DB_PATH` | SQLite file | `./data/clients.db` |
| `TAVILY_API_KEY` | Tavily search (optional) | — |
| `FX_API_BASE` | FX rates endpoint | `https://open.er-api.com/v6/latest` |

## Run

Open **two terminals** (the MCP server is a separate remote process):

```bash
# Terminal 1 — start the remote MCP server
make mcp-server          # → http://0.0.0.0:8000/mcp

# (optional) seed some sample clients
make seed

# Terminal 2 — chat with the agent
make chat                # interactive REPL
# or a one-off:
python -m agentic_app.main "Add a client: Acme Corp, USA, California, SF, +1-415-555-0100"
```

Example prompts the agent can handle end-to-end:

- "Store a new client: Globex Ltd, UK, England, contact@globex.example."
  (`name`, `country`, `state`, and `email` are **required**; city and phone are optional.)
- "List all clients in India." / "Search clients named acme."
- "What's the latest news on the OpenAI Agents SDK?" (web search)
- "Convert 250 EUR to INR." (currency tool)

## Tool-usage tracking

Every query prints which capability answered it. As each tool fires, a live line
shows its category — **MCP** (client directory), **WEB** (web search), or
**CUSTOM** (currency) — followed by a per-turn and per-session summary:

```
you › find clients in London and convert their retainer of 5000 GBP to USD
  [MCP] → search_clients
  [MCP] ✓ search_clients · 42ms
  [CUSTOM] → convert_currency
  [CUSTOM] ✓ convert_currency · 310ms
assistant › …
  tools used → MCP×1, CUSTOM×1
  session totals → mcp×1, custom×1
```

This is implemented with the Agents SDK lifecycle hooks (`on_tool_start` /
`on_tool_end`) in `src/agentic_app/tracking.py`. `ToolUsageTracker` also keeps a
structured record (`.calls`, `.counts()`) you can wire into logging or telemetry.

## Observability (Langfuse)

Optional LLM tracing via [Langfuse](https://langfuse.com). It instruments the
OpenAI Agents SDK over OpenTelemetry, so **every agent run, LLM call, and tool
call** (MCP client-directory ops, web search, currency) shows up as a span with
inputs, outputs, latency, and token usage — no per-call code.

```bash
pip install -e ".[observability]"
# then set in .env:
#   LANGFUSE_PUBLIC_KEY=pk-lf-...
#   LANGFUSE_SECRET_KEY=sk-lf-...
#   LANGFUSE_HOST=https://cloud.langfuse.com   # or your self-hosted / US host
```

Tracing is **fully optional and gated**: with no keys it's a silent no-op and the
app runs exactly as before. Buffered spans are flushed automatically on exit.
Implementation lives in `src/agentic_app/observability.py`. This complements the
in-terminal tool-usage tracker above: the tracker gives an instant per-turn
readout, Langfuse gives durable, searchable traces.

## Testing

```bash
make test        # storage-layer unit tests (no network / no API key needed)
make lint        # ruff
```

## Notes

- The MCP server is a genuine **remote** server (streamable-HTTP), so it can run on a
  different host/container than the agent — just point `MCP_SERVER_URL` at it.
- Tools **degrade gracefully**: a missing Tavily key or an unreachable FX endpoint
  returns a structured error the agent can reason about (e.g. fall back to DuckDuckGo)
  rather than crashing.
- The SQLite storage layer opens a short-lived connection per operation, making it safe
  under FastMCP's worker threads.
