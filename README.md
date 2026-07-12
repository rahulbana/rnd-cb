# rnd-cb — Memory Chatbot Agent

A CLI chatbot agent with **short-term** and **long-term** memory, built with
**Python + OpenAI + LangGraph**. Multiple users can share one install — each
gets a private conversation and a private long-term memory. Every message is
archived to SQLite.

## How memory works

| Tier | What it holds | Where it lives | Lifetime |
|------|---------------|----------------|----------|
| **Short-term** | The running conversation (recent turns) | LangGraph SQLite **checkpointer**, keyed by a per-user *thread* | Persists across restarts; reset with `/new` |
| **Long-term** | Durable facts about the user (name, preferences, projects…) | `long_term_memory` table with OpenAI **embeddings** | Forever, until deleted |
| **Archive** | Every message ever sent | `messages` table | Forever |

On each turn the agent:

1. **Recalls** the most semantically-relevant long-term memories for your
   message (cosine similarity over embeddings) and injects them into the
   system prompt.
2. **Windows** the running conversation to the last `SHORT_TERM_WINDOW`
   messages before calling the model (keeps the context focused and cheap).
3. Lets the model **save new facts** via the `save_memory` tool and dig for
   more via `search_long_term_memory`.

### Graph

```
START ─▶ recall ─▶ agent ─▶ (tools ─▶ agent)* ─▶ END
```

## Tools

The agent can call these when they help (memory tools plus utilities):

| Tool | What it does | Needs |
|------|--------------|-------|
| `save_memory` / `search_long_term_memory` | Store & recall durable user facts | — |
| `web_search` | Live web search via **Tavily** | `TAVILY_API_KEY` |
| `convert_currency` | Live FX conversion (ISO codes) | network (open.er-api.com) |
| `convert_units` | Length/mass/temp/volume/… via **pint** | — |
| `current_time` | Time by IANA zone, city, or country | — |
| `ip_lookup` | Resolve a domain/URL to IP(s) + geolocation | network |
| `draft_email` | Draft an email from key points | — |
| `summarize_text` | Summarize a block of text | — |
| `translate_text` | Translate text to a target language | — |

`draft_email`, `summarize_text`, and `translate_text` run a focused, tool-free
sub-call to the same model, keeping the main conversation context clean. Every
tool degrades gracefully — a missing key or network hiccup returns a readable
message instead of crashing the chat.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # then put your OPENAI_API_KEY in .env
```

## Run

```bash
python -m memory_agent
```

You'll be asked for a username (this is the `user_id` that scopes memory).
Then just chat. In-chat commands:

```
/help        show commands
/memories    list what I remember about you long-term
/history     show your recent chat archive
/new         start a fresh conversation (keeps long-term memory)
/whoami      show your user id / thread
/switch      switch to a different user
/exit        quit
```

### Example

```
alice> Hi, I'm Alice and I'm allergic to peanuts.
bot> Nice to meet you, Alice! I'll remember your peanut allergy. ...
      (saved to long-term memory: "User's name is Alice";
                                   "User is allergic to peanuts")

# ...restart the program later, same username...

alice> Suggest a snack for me.
bot> Since you're allergic to peanuts, how about ... (recalled from long-term memory)
```

## Observability (Langfuse)

Optional. Set `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` (and
`LANGFUSE_HOST` for self-hosted) to trace every run to
[Langfuse](https://langfuse.com) — LLM calls, tool calls, latencies, and
token/cost — grouped by **user** (`user_id`) and **session** (the conversation
thread). It attaches as a LangChain callback, so no code paths change.

With no keys set, tracing is silently disabled and the app runs unchanged; a
misconfigured tracer never breaks the chat. When enabled, the startup banner
shows `observability: Langfuse tracing enabled`.

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

The suite (`tests/`) is fully offline — the OpenAI chat and embedding models are
replaced with deterministic fakes and HTTP-backed tools are monkeypatched, so no
API key or network is needed. It covers storage + semantic recall, every tool,
the graph (tool routing, short-term persistence, memory recall), and the CLI.

## Configuration

All settings are environment variables (see `.env.example`): model names,
`OPENAI_BASE_URL` for OpenAI-compatible gateways, the SQLite path, and memory
tuning (`SHORT_TERM_WINDOW`, `MEMORY_TOP_K`, `MEMORY_MIN_SCORE`).

## Layout

```
memory_agent/
  config.py              settings from env / .env
  models.py              OpenAI chat + embedding model factories
  observability.py       optional Langfuse tracing (callback + trace metadata)
  storage/
    database.py          SQLite: chat archive + long-term memory rows
    long_term_memory.py  embed, store, vectorised semantic recall
  tools/
    base.py              shared helpers (HTTP, LLM sub-task, host parsing)
    memory.py            save_memory / search_long_term_memory
    web.py               web_search (Tavily)
    converters.py        convert_currency / convert_units
    datetime_tools.py    current_time
    network.py           ip_lookup
    text.py              draft_email / summarize_text / translate_text
    __init__.py          build_tools() — tool registry
  agent/
    state.py             graph state schema
    prompts.py           system prompt
    graph.py             build_agent() — nodes + wiring
  cli/
    session.py           per-user session state
    commands.py          slash-command helpers
    app.py               interactive chat loop
```

Adding a capability is a self-contained change: write a `make_*_tools` factory
in a `tools/` module and register it in `tools/__init__.py`.
