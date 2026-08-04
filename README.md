# RND CB — Desktop AI Coding Agent

A **desktop AI coding agent** with a **FastAPI + Python** backend and an
**Electron + React + TypeScript** frontend, powered by the **OpenAI** API, with
optional **Postgres**-backed conversation history.

The agent can explore your project, read and edit files, and run shell commands in a
directory you choose — all from a chat interface, with an approval gate for anything
that changes your machine.

![frontend](https://img.shields.io/badge/Electron-React-blue) ![backend](https://img.shields.io/badge/FastAPI-Python-009688) ![lang](https://img.shields.io/badge/TypeScript-strict-3178c6)

## Features

- 💬 **Chat + code generation** — conversational assistant that explains and writes code.
- 📂 **Read & edit local files** — the agent works inside a project directory you select.
- ⚡ **Run commands** — build, test, run `git`, install deps; output is fed back to the model.
- 🔒 **Approval gate** — file writes and shell commands prompt for approval (toggle to auto).
- 🗄 **Persistent history (Postgres)** — conversations and messages are saved.
  Runs fine in-memory if you don't configure a database.
- 🧰 **Tool-use loop** — OpenAI function calling drives `list_files`, `read_file`,
  `write_file`, and `run_command` until the task is done.

## Architecture

```
┌──────────── Electron desktop shell ────────────┐
│                                                 │
│  Renderer (React/TS)                            │
│  ┌───────────────┐   REST  +  WebSocket         │
│  │ Chat UI       │──────────────────────┐       │
│  │ Sidebar       │                       │       │
│  │ Approval modal│                       ▼       │
│  └───────────────┘        ┌────────────────────────────┐
│  Main process              │  FastAPI backend (Python)  │
│  · spawns backend ─────────▶  · OpenAI agent loop       │
│  · native dir picker       │  · fs + shell tools        │
│                            │  · Postgres persistence    │
└────────────────────────────┴─────────────┬──────────────┘
                                            ▼
                                   OpenAI API  +  Postgres
```

The repo is split into two top-level directories:

```
rnd-cb/
├── backend/     FastAPI + Python service
└── frontend/    Electron + React + TypeScript desktop app
```

- **`backend/`** — FastAPI service: the OpenAI agent loop, filesystem/shell tools,
  Postgres persistence, REST endpoints, and a `/ws/agent` WebSocket that streams
  agent events and negotiates approvals.
- **`frontend/src/main`** — Electron main process: spawns & supervises the Python
  backend and provides the native folder picker.
- **`frontend/src/preload`** — secure `contextBridge` exposing `window.desktop`
  (backend URL + directory picker).
- **`frontend/src/renderer`** — React UI that talks to the backend over REST +
  WebSocket (`frontend/src/renderer/src/api/client.ts`).
- **`frontend/src/shared`** — types shared across the frontend.

### Backend API

| Method / Channel                                  | Purpose                                  |
| ------------------------------------------------- | ---------------------------------------- |
| `GET /api/health`                                 | Readiness probe (used by Electron).      |
| `GET /api/settings`                               | Current settings + API-key/DB status.    |
| `POST /api/settings/model`                        | Change the model.                        |
| `POST /api/settings/permission-mode`              | Switch `ask` / `auto`.                   |
| `POST /api/settings/project-path`                 | Set the project directory.               |
| `GET /api/conversations`                          | List conversations.                      |
| `GET /api/conversations/{id}/messages`            | Message history.                         |
| `DELETE /api/conversations/{id}`                  | Delete a conversation.                   |
| `WS /ws/agent`                                    | Run the agent; stream events; approvals. |

WebSocket messages — client → server: `run`, `approval`, `cancel`. Server → client:
`assistant_text`, `tool_call`, `tool_result`, `error`, `done`, `approval_request`,
`conversation_created`.

## Prerequisites

- **Node.js 18+** (built/tested on Node 22)
- **Python 3.10+** (built/tested on Python 3.11)
- An **OpenAI API key**
- *(Optional)* **PostgreSQL 13+** for persistent history

## Setup

```bash
# 1. Frontend dependencies
cd frontend
npm install
cd ..

# 2. Backend dependencies (into a virtualenv is recommended)
python3 -m venv backend/.venv
source backend/.venv/bin/activate        # Windows: backend\.venv\Scripts\activate
pip install -r backend/requirements.txt

# 3. Configure the backend
cp backend/.env.example backend/.env
#    then edit backend/.env and set at least OPENAI_API_KEY
#    (add DATABASE_URL to enable persistent history)

# 4. Run the app (Electron spawns the backend for you)
cd frontend
npm run dev
```

> Electron launches the Python backend automatically using `python3` (override with
> `PYTHON=...`). Make sure the backend's dependencies are importable by that
> interpreter — either activate the venv before `npm run dev`, or point `PYTHON` at
> the venv's Python.

### Running the backend separately (dev)

If you prefer to run the backend yourself (e.g. with `--reload`):

```bash
# terminal 1 — from the backend directory
source backend/.venv/bin/activate
cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# terminal 2 — from the frontend directory; tell Electron to connect, not spawn
cd frontend && BACKEND_URL=http://127.0.0.1:8000 npm run dev
```

### Configuration

Backend settings live in **`backend/.env`** (see `backend/.env.example`):

| Variable                | Required | Description                                                      |
| ----------------------- | -------- | ---------------------------------------------------------------- |
| `OPENAI_API_KEY`        | ✅       | Your OpenAI API key.                                             |
| `OPENAI_MODEL`          | ➖       | Default model (also switchable in the UI). Defaults to `gpt-4o`. |
| `DATABASE_URL`          | ➖       | Postgres connection string. Omit for in-memory history.         |
| `PROJECT_DIR`           | ➖       | Default directory the agent operates in. Changeable in the UI.  |
| `AGENT_PERMISSION_MODE` | ➖       | `ask` (default) or `auto` for side-effecting tools.             |
| `VENV_PYTHON`           | ➖       | Interpreter used to create a project's virtualenv. Default `python3.12`. |

Frontend/spawn settings live in the repo-root **`.env`** (see `.env.example`):
`BACKEND_HOST`, `BACKEND_PORT`, `BACKEND_URL`, `PYTHON`.

## Usage

1. Launch with `npm run dev`.
2. **＋ New project** creates a fresh project folder and offers to create a Python
   virtual environment (`.venv`) for it using `python3.12` (configurable via
   `VENV_PYTHON`). Or use the **📁** button to open an existing folder.
3. In the top bar, pick your **model** and **approval mode**.
3. Ask the agent to do something, e.g.:
   - *"List the files and summarize what this project does."*
   - *"Add a `/health` endpoint and write a test for it."*
   - *"Run the test suite and fix any failures."*
4. In `ask` mode you'll get an approval dialog before any **file write** or **command**.

## Scripts

Run these from the **`frontend/`** directory:

| Script                     | Description                                        |
| -------------------------- | -------------------------------------------------- |
| `npm run dev`              | Run Electron (which spawns the backend).           |
| `npm run backend`          | Run the FastAPI backend with hot reload.           |
| `npm run backend:install`  | Install backend Python dependencies.               |
| `npm run build`            | Type-check and bundle the frontend.                |
| `npm run typecheck`        | Type-check the Node and web sources.               |
| `npm run package`          | Build and package a distributable (electron-builder). |

## Security notes

- The agent's file access is **sandboxed to the selected project directory** — path
  traversal outside the root is rejected by the backend.
- `write_file` and `run_command` are **gated by an approval dialog** in the default
  `ask` mode. Only switch to `auto` for trusted workflows.
- Shell commands run with the backend process's permissions inside the project
  directory, with an output cap and a timeout. Review commands before approving them.
- The backend binds to `127.0.0.1` only. Your API key is read from `backend/.env` and
  is never sent anywhere except OpenAI.

## Data model (Postgres)

- `conversations(id, title, project_path, created_at, updated_at)`
- `messages(id, conversation_id, role, content, tool_calls, tool_call_id, name, created_at)`

The schema is created automatically on backend startup (`backend/app/schema.sql`).

## License

MIT
