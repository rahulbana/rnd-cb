# AutoDev — Autonomous AI Code Generator

AutoDev is a local, desktop-style application that **autonomously builds whole
software projects from a single natural-language prompt** — in any programming
language. You describe what you want ("a CLI todo app in Python", "a REST API
for a bookstore in Go"), and AutoDev plans it, generates the code in an
**isolated per-project sandbox**, sets up the environment, **writes and runs
automated tests, and fixes its own failures** until the project works — while
streaming everything live to the UI.

Because the FastAPI engine is always-on, runs continue **in the background even
if you close the UI**. Reopen it any time and the full progress history is
replayed from the database.

---

## Highlights

- 🧠 **Fully autonomous loop:** `plan → generate → setup env → test → fix → repeat`
- 🧑‍⚖️ **Optional human-in-the-loop:** a toggle to pause after planning so you can
  approve or revise the plan before any code is written.
- 🧩 **Incremental generation:** large projects are built file-by-file (each
  file sees the ones before it) instead of one giant call, for coherence and to
  stay within model output limits.
- 🌍 **Language-agnostic:** the agent chooses the stack and its native tooling
  (pytest, `go test`, `node --test`, …).
- 📦 **Isolated sandbox per project:** each project gets its own directory and,
  for Python, its own virtualenv. Commands run as sandboxed subprocesses with
  wall-clock timeouts. Path-escape attempts are blocked.
- 🔀 **Pluggable LLM:** OpenAI *and* Ollama, swappable via one env var, unified
  streaming for both.
- ⏯️ **Background + resumable:** every step is persisted to SQLite and streamed
  over WebSocket. Close the app, reopen later, see exactly what happened.
- 🧪 **It tests itself:** AutoDev generates real tests and executes them; on
  failure it feeds the output back to the model and patches the code.
- 🗂️ **Optional long-term memory:** ChromaDB + sentence-transformers, lazily
  loaded, so the core app stays lightweight.

---

## Architecture

```
autodev/
├── config.py            # env-driven settings (AUTODEV_* )
├── database.py          # SQLAlchemy engine + session scope (SQLite → Postgres-ready)
├── models.py            # Project, Event, Artifact, Message
├── schemas.py           # API request models
├── main.py              # FastAPI app factory + lifespan (DB init, orphan recovery)
├── llm/
│   ├── base.py          # provider-agnostic streaming contract
│   ├── openai_provider.py
│   ├── ollama_provider.py
│   └── factory.py
├── sandbox/
│   ├── manager.py       # per-project dir + venv + safe path resolution
│   └── executor.py      # async subprocess runner with timeout + line streaming
├── agent/
│   ├── prompts.py       # portable structured-JSON prompt protocol
│   ├── parsing.py       # robust JSON extraction from model output
│   └── orchestrator.py  # the autonomous build loop
├── memory/store.py      # optional ChromaDB vector memory (no-op if disabled)
├── services/
│   ├── event_bus.py     # in-process pub/sub for live streaming
│   ├── events.py        # persist-and-publish event helper
│   ├── run_manager.py   # background asyncio runs + startup recovery
│   └── project_service.py
├── api/routes.py        # REST + WebSocket
└── web/static/          # single-page streaming UI (no build step, no CDN)
```

**Why runs survive a UI close:** the browser is just a view. The FastAPI
process owns the agent tasks and writes an append-only `Event` log (with a
per-project sequence number) to SQLite. On reconnect the UI replays the backlog
by sequence, then subscribes to the live tap. If the *server* process is
restarted mid-run, interrupted runs are marked `stopped` on startup so the UI
stays honest and you can re-run with one click.

---

## Quickstart

Requires Python 3.10+.

```bash
# 1. Install core dependencies
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
#    edit .env — set AUTODEV_OPENAI_API_KEY, or switch to Ollama (below)

# 3. Launch (opens the UI in your browser)
python run.py
```

Then type a prompt like *"a simple desktop app"* or *"a FastAPI URL shortener
with tests"* and watch it build.

### Using Ollama instead of OpenAI

```dotenv
AUTODEV_LLM_PROVIDER=ollama
AUTODEV_OLLAMA_BASE_URL=http://localhost:11434
AUTODEV_OLLAMA_MODEL=llama3.1
```

No API key required. Make sure `ollama serve` is running and the model is pulled.

### Optional long-term memory

```bash
pip install -r requirements-memory.txt
```
```dotenv
AUTODEV_MEMORY_ENABLED=true
```

---

## Human-in-the-loop plan approval

Turn it on per build with the **"Review plan before building"** checkbox (its
state is remembered), or set the default with `AUTODEV_REQUIRE_PLAN_APPROVAL`.

When enabled, the agent plans, then **pauses at an `awaiting_approval` state**
instead of writing code. In the UI you get an approval bar:

- **Approve & build** → generation resumes from the approved plan.
- **Revise** (with a note) → the agent re-plans incorporating your feedback and
  pauses again for approval.

The plan is persisted, so the gate **survives an app restart** — you can approve
hours later. Nothing is generated and no sandbox commands run until you approve.

## Incremental generation

Controlled by `AUTODEV_INCREMENTAL_GENERATION`:

- **`auto`** (default) — single-shot for small projects; switches to
  file-by-file once the plan lists more than `AUTODEV_INCREMENTAL_FILE_THRESHOLD`
  files.
- **`always`** — always file-by-file (best coherence for large projects).
- **`never`** — always a single generation call (fastest, smallest projects).

In file-by-file mode each file is generated with the already-written files as
context, which keeps a large codebase self-consistent and avoids hitting the
model's single-response output limit.

---

## Configuration

All settings are environment variables prefixed with `AUTODEV_` (see
`.env.example`). Key ones:

| Variable | Default | Purpose |
|---|---|---|
| `AUTODEV_LLM_PROVIDER` | `openai` | `openai` or `ollama` |
| `AUTODEV_OPENAI_API_KEY` | — | required for OpenAI |
| `AUTODEV_OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model |
| `AUTODEV_OLLAMA_MODEL` | `llama3.1` | Ollama model |
| `AUTODEV_MAX_FIX_ITERATIONS` | `4` | test→fix retries |
| `AUTODEV_REQUIRE_PLAN_APPROVAL` | `false` | default: pause for plan approval |
| `AUTODEV_INCREMENTAL_GENERATION` | `auto` | `auto` / `always` / `never` |
| `AUTODEV_INCREMENTAL_FILE_THRESHOLD` | `6` | `auto` switches to file-by-file above this |
| `AUTODEV_WORKSPACE_ROOT` | `./workspaces` | where sandboxes live |
| `AUTODEV_COMMAND_TIMEOUT` | `300` | max seconds per sandbox command |
| `AUTODEV_DATABASE_URL` | `sqlite:///./autodev.db` | swap for Postgres later |

Postgres is a drop-in later: point `AUTODEV_DATABASE_URL` at a Postgres DSN
(the ORM is engine-agnostic).

---

## HTTP / WebSocket API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/projects` | create a project (`auto_start` builds immediately) |
| `GET` | `/api/projects` | list projects (with live `running` flag) |
| `GET` | `/api/projects/{id}` | project detail + artifacts + messages |
| `GET` | `/api/projects/{id}/events?after={seq}` | replay persisted events |
| `GET` | `/api/projects/{id}/files?path=…` | read a generated file |
| `POST` | `/api/projects/{id}/run` | (re)start a background run |
| `POST` | `/api/projects/{id}/approve` | approve a pending plan and build |
| `POST` | `/api/projects/{id}/revise` | re-plan with `{"feedback": …}` |
| `POST` | `/api/projects/{id}/stop` | stop a run |
| `DELETE` | `/api/projects/{id}` | delete project + sandbox |
| `WS` | `/ws/projects/{id}` | live event stream (send `{"after": seq}` to resume) |

---

## Testing

The suite runs fully offline using a stub LLM, but exercises the **real**
orchestrator, sandbox, venv creation and subprocess test execution:

```bash
pip install pytest
python -m pytest tests/ -v
```

- `test_agent_e2e.py` — builds a real project end-to-end, creates a venv, runs
  its tests, and verifies the fix-loop recovers from an intentionally broken
  first generation.
- `test_sandbox.py` — sandbox isolation + path-escape protection.
- `test_parsing.py` — resilient JSON extraction from messy model output.

---

## Safety notes

The agent executes model-generated code as subprocesses on your machine (inside
per-project directories, with timeouts). Run it on projects and prompts you
trust. A Docker-backed executor is a natural next step for stronger isolation —
the executor is already abstracted behind `sandbox/executor.py`.

## Roadmap

- Docker/gVisor sandbox backend (opt-in, stronger isolation)
- Postgres + pgvector for persistence and memory
- Per-file approval / diff review during generation
- Packaging as a native shell (Tauri/Electron)
