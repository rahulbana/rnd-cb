# RND CB — Desktop AI Coding Agent

A cross-platform **desktop AI coding agent** built with **Electron + React + TypeScript**,
powered by the **OpenAI** API, with optional **Postgres**-backed conversation history.

The agent can explore your project, read and edit files, and run shell commands in a
directory you choose — all from a chat interface, with an approval gate for anything
that changes your machine.

![architecture](https://img.shields.io/badge/Electron-React-blue) ![lang](https://img.shields.io/badge/TypeScript-strict-3178c6)

## Features

- 💬 **Chat + code generation** — conversational assistant that explains and writes code.
- 📂 **Read & edit local files** — the agent works inside a project directory you select.
- ⚡ **Run commands** — build, test, run `git`, install deps; output is fed back to the model.
- 🔒 **Approval gate** — file writes and shell commands prompt for approval (toggle to auto).
- 🗄 **Persistent history (Postgres)** — conversations and messages are saved and searchable.
  Runs fine in-memory if you don't configure a database.
- 🧰 **Tool-use loop** — OpenAI function calling drives `list_files`, `read_file`,
  `write_file`, and `run_command` until the task is done.

## Architecture

```
┌────────────────────── Electron ──────────────────────┐
│  Renderer (React/TS)        Main process (Node/TS)    │
│  ┌───────────────┐  IPC     ┌───────────────────────┐ │
│  │ Chat UI       │◄────────►│ Agent loop (OpenAI)   │ │
│  │ Sidebar       │  events  │  tools: fs + shell    │ │
│  │ Approval modal│          │ Postgres repository   │ │
│  └───────────────┘          └───────────┬───────────┘ │
└──────────────────────────────────────────┼───────────┘
                                            ▼
                                    OpenAI API  +  Postgres
```

- `src/main` — Electron main process: OpenAI agent loop, filesystem/shell tools,
  Postgres persistence, and IPC handlers.
- `src/preload` — secure `contextBridge` exposing a typed `window.api`.
- `src/renderer` — React UI (chat, sidebar, top bar, approval modal).
- `src/shared` — types shared across all three.

## Prerequisites

- **Node.js 18+** (built and tested on Node 22)
- An **OpenAI API key**
- *(Optional)* **PostgreSQL 13+** for persistent history

## Setup

```bash
# 1. Install dependencies
npm install

# 2. Configure environment
cp .env.example .env
#    then edit .env and set at least OPENAI_API_KEY

# 3. (Optional) Create the Postgres schema
#    Requires DATABASE_URL in .env
npm run db:init

# 4. Run in development (hot reload)
npm run dev
```

### Environment variables (`.env`)

| Variable                 | Required | Description                                                        |
| ------------------------ | -------- | ------------------------------------------------------------------ |
| `OPENAI_API_KEY`         | ✅       | Your OpenAI API key.                                               |
| `OPENAI_MODEL`           | ➖       | Default model (also switchable in the UI). Defaults to `gpt-4o`.   |
| `DATABASE_URL`           | ➖       | Postgres connection string. Omit to run with in-memory history.   |
| `PROJECT_DIR`            | ➖       | Default directory the agent operates in. Changeable in the UI.     |
| `AGENT_PERMISSION_MODE`  | ➖       | `ask` (default) or `auto` for side-effecting tools.                |

## Usage

1. Launch with `npm run dev`.
2. In the top bar, pick your **project folder**, **model**, and **approval mode**.
3. Ask the agent to do something, e.g.:
   - *"List the files and summarize what this project does."*
   - *"Add a `/health` endpoint and write a test for it."*
   - *"Run the test suite and fix any failures."*
4. When the agent wants to **write a file** or **run a command** in `ask` mode,
   you'll get an approval dialog with the details before it proceeds.

## Scripts

| Script              | Description                                       |
| ------------------- | ------------------------------------------------- |
| `npm run dev`       | Run the app in development with hot reload.       |
| `npm run build`     | Type-check and bundle main/preload/renderer.      |
| `npm run start`     | Preview the production build.                     |
| `npm run typecheck` | Type-check the Node and web sources.              |
| `npm run db:init`   | Create/verify the Postgres schema.                |
| `npm run package`   | Build and package a distributable (electron-builder). |

## Security notes

- The agent's file access is **sandboxed to the selected project directory** — path
  traversal outside the root is rejected.
- `write_file` and `run_command` are **gated by an approval dialog** in the default
  `ask` mode. Only switch to `auto` for trusted workflows.
- Shell commands run with your user's permissions inside the project directory, with an
  output cap and a timeout. Review commands before approving them.
- Your API key is read from the environment/`.env` and is never sent anywhere except OpenAI.

## Data model (Postgres)

- `conversations(id, title, project_path, created_at, updated_at)`
- `messages(id, conversation_id, role, content, tool_calls, tool_call_id, name, created_at)`

## License

MIT
