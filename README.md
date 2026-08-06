# AI Agent — Desktop Multi-Tool Assistant

A modular, desktop AI agent with a responsive chat UI. It uses an **OpenAI**
tool-calling loop to orchestrate **23 tools** — web search, weather, currency &
unit conversion, notes, fact-checking, translation, and more. Built with
**Python** (FastAPI + pywebview) and a clean vanilla-JS frontend.

<p align="center">
  <em>Native desktop window &nbsp;·&nbsp; local FastAPI backend &nbsp;·&nbsp; 23 modular tools</em>
</p>

---

## ✨ Features / Tools

| Category | Tools |
|---|---|
| **Research** | `web_search`, `deep_web_search` (reads pages + cites), `verify_claim` (fact-checker), `get_news_headlines`, `save_research` (txt/md/json/xml/csv/xlsx/docx/pptx/pdf) |
| **Reference** | `get_country_summary` (capital, population, leaders…), `get_time_in_country` |
| **Weather & Environment** | `get_current_temperature`, `get_air_quality` |
| **Converters** | `convert_currency` (USD→INR…), `convert_measurement` (100cm→m…) |
| **Language** | `translate_text`, `summarize_text` |
| **Notes** | `create_note`, `list_notes`, `search_notes`, `delete_note` |
| **Calendar** | `get_events_on_date` (this-day-in-history), `get_festival_date`, `get_public_holidays`, `calculate_age` |
| **Media** | `resize_image` (by ratio or dimensions) |
| **System** | `get_system_health` (CPU / RAM / disk / battery) |

Every tool is callable two ways:
1. **Through chat** — the agent decides which tool(s) to call and chains them.
2. **Directly** — click any tool in the sidebar to run it with a form (works
   even without an OpenAI key).

## 🤖 LLM provider (OpenAI or Ollama)

The agent works with **OpenAI** or a **local Ollama** model. Pick one in the
sidebar **Model** selector (or set `LLM_PROVIDER` in `.env`), and type the model
name below it. Switching is live — no restart needed.

- **OpenAI** — set `OPENAI_API_KEY` and a model (e.g. `gpt-4o-mini`).
- **Ollama** — run `ollama serve` locally, no key needed. Use a **tool-capable**
  model (e.g. `llama3.1`, `qwen2.5`, `mistral-nemo`) for tool calling to work.
  Configure `OLLAMA_BASE_URL` / `OLLAMA_MODEL` in `.env` if needed.

## 🗝️ API keys

Only an **LLM provider** is required (OpenAI key, or a local Ollama server) for
chat, translation, summarizing and fact-checking. Every data tool uses a
**free, key-less public API**:

| Data | Provider |
|---|---|
| Web search | DuckDuckGo (`ddgs`) |
| Weather / air quality / geocoding | Open-Meteo |
| Country facts | REST Countries + Wikipedia |
| Currency rates | open.er-api.com |
| Public holidays | Nager.Date |
| History (on this day) | muffinlabs |
| News | Google News RSS |

Optional: `CALENDARIFIC_API_KEY` improves the festival-date tool (otherwise it
falls back to the LLM). See [`.env.example`](.env.example).

## 🚀 Quick start

```bash
# 1. Create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure your key
cp .env.example .env               # then edit .env and add OPENAI_API_KEY

# 3. Run
python run.py                      # native desktop window
python run.py --web                # open in your browser instead
python run.py --server             # headless server only (dev/tests)
```

> The desktop window uses **pywebview**. On Linux it needs a GTK or Qt backend
> (`pip install pywebview[qt]` or `[gtk]`). If a window can't be created, the
> app automatically falls back to browser mode.

## 🏗️ Architecture

```
run.py                     # entry point: starts server + desktop window
app/
├── config.py              # env/.env configuration
├── server.py              # FastAPI: /api/chat, /api/tools, /api/tool/{name}
├── agent/
│   ├── client.py          # OpenAI client wrapper
│   └── orchestrator.py    # the tool-calling loop
├── tools/                 # one module per capability
│   ├── base.py            # Tool descriptor + shared HTTP helpers
│   ├── __init__.py        # registry: discovers all tools
│   ├── web_search.py  weather.py  air_quality.py  currency.py …
│   └── …
├── storage/db.py          # SQLite persistence for notes
└── frontend/              # responsive UI (index.html, styles.css, app.js)
```

**Adding a tool** is a 2-step process:
1. Create `app/tools/my_tool.py` exposing `get_tools() -> list[Tool]`.
2. Add the module to `_MODULES` in `app/tools/__init__.py`.

The tool is then automatically available to the agent *and* in the UI sidebar —
its input form is generated from the JSON schema you declare.

## 🔌 API endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/api/status` | LLM configured? model, tool count |
| `GET`  | `/api/tools` | tool metadata grouped by category |
| `POST` | `/api/chat` | `{messages:[{role,content}]}` → agent reply + tool trace (non-streaming) |
| `POST` | `/api/chat/stream` | same body → **Server-Sent Events**: `token`, `tool_call`, `tool_result`, `done`, `error` |
| `POST` | `/api/tool/{name}` | `{arguments:{…}}` → run one tool directly |
| `POST` | `/api/open` | `{path, reveal}` → open a file with its default app, or reveal it in the OS file manager |
| `POST` | `/api/upload` | multipart file → saves to `uploads/`, returns its path |
| `GET`  | `/api/settings` | current LLM provider, model, and available providers |
| `POST` | `/api/settings` | `{provider, model}` → switch provider/model at runtime |

### File upload

Click the 📎 in the chat composer to attach a file — its uploaded path is
referenced in your message so the agent can act on it (e.g. summarize a PDF/Word
doc, resize an image). In the direct tool panel, any file-path field (like
`resize_image`'s `path` or `summarize_text`'s `file_path`) shows an **Upload**
button that fills the field with the uploaded file's path. `summarize_text`
accepts a `file_path` and reads txt, md, csv, json, xml, docx and pdf.

When a tool produces a file (e.g. `save_research`, `resize_image`), the UI
shows **Open file** and **Open directory** buttons — in both the chat and the
direct tool panel — that call `/api/open` to launch the file or reveal it in
the system file manager (Windows Explorer `/select`, macOS `open -R`, Linux
`xdg-open`).

The UI uses `/api/chat/stream` by default, so replies **stream in token-by-token**
and tool chips appear live as the agent runs each tool. `/api/chat` remains for
non-streaming clients.

### Conversation persistence

Conversations are saved to SQLite and listed in the sidebar, so you can revisit
past chats after restarting the app. A conversation is created lazily on your
first message; the user turn is persisted before streaming and the assistant
reply on completion.

| Method | Path | Purpose |
|---|---|---|
| `GET`    | `/api/conversations` | list saved conversations (most recent first) |
| `POST`   | `/api/conversations` | create a conversation `{title?}` |
| `GET`    | `/api/conversations/{id}` | conversation + its messages |
| `PATCH`  | `/api/conversations/{id}` | rename `{title}` |
| `DELETE` | `/api/conversations/{id}` | delete a conversation and its messages |

## 🪵 Logging

Errors and activity are written to **date-wise log files** under `logs/`:

```
logs/agent-YYYY-MM-DD.log     all activity (tool calls, requests) at LOG_LEVEL
logs/errors-YYYY-MM-DD.log    errors and exceptions only, with full tracebacks
```

A new file is started automatically each day, and files older than
`LOG_RETENTION_DAYS` (default 30) are pruned on startup. Uncaught exceptions,
tool failures, LLM errors and unhandled request errors are all captured.
Configure via `LOG_LEVEL`, `LOG_DIR` and `LOG_RETENTION_DAYS` in `.env`.

## 🧪 Notes on the environment

Data tools require outbound internet access. Behind a restrictive network
policy some public APIs may be blocked; running on a normal desktop connection
resolves this. The app degrades gracefully — a failing tool returns a structured
error rather than crashing the agent.
