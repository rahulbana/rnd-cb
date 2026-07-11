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

## Configuration

All settings are environment variables (see `.env.example`): model names,
`OPENAI_BASE_URL` for OpenAI-compatible gateways, the SQLite path, and memory
tuning (`SHORT_TERM_WINDOW`, `MEMORY_TOP_K`, `MEMORY_MIN_SCORE`).

## Layout

```
memory_agent/
  config.py   settings from env / .env
  db.py       SQLite: chat archive + long-term memory rows
  memory.py   long-term memory: embed, store, semantic recall
  agent.py    LangGraph graph, LLM, and memory tools
  cli.py      interactive chat loop
```
