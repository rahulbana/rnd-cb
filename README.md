# Multi-Agent Code Generator

Describe a programming problem, pick a language, and a pipeline of AI agents
will **plan**, **write**, and **review** a well-documented solution for you.

The reviewer agent specifically hardens the generated code: it checks for
bugs, ensures inputs are **validated**, ensures failures are handled with
idiomatic **exception/error handling**, and ensures the function is **clearly
documented**.

## Architecture

```
React (frontend)  ──HTTP──▶  FastAPI (backend)  ──▶  Multi-agent pipeline ──▶ OpenAI
                                                       1. Planner  → plan
                                                       2. Coder    → draft code
                                                       3. Reviewer → final code + notes
```

| Layer    | Tech                                   |
| -------- | -------------------------------------- |
| Frontend | React (Create React App)               |
| Backend  | Python, FastAPI, Pydantic              |
| LLM      | OpenAI Chat Completions API            |

### The agents

1. **Planner** (`app/agents/planner.py`) — turns the problem statement into an
   ordered implementation plan that explicitly calls out validation, edge
   cases, error handling, and documentation.
2. **Coder** (`app/agents/coder.py`) — writes a self-contained function/method
   that follows the plan, with validation, exception handling, doc-comments,
   and a usage example.
3. **Reviewer** (`app/agents/reviewer.py`) — critiques the draft for bugs,
   missing validation, weak error handling, and poor docs, then returns a
   corrected version plus a list of what it changed.

The agents are coordinated by `app/services/orchestrator.py`.

## Getting started

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env                                # then add your OpenAI key
uvicorn app.main:app --reload --port 8000
```

Environment variables (see `backend/.env.example`):

| Variable             | Default                 | Description                      |
| -------------------- | ----------------------- | -------------------------------- |
| `OPENAI_API_KEY`     | _(required)_            | Your OpenAI API key.             |
| `OPENAI_MODEL`       | `gpt-4o`                | Chat model used by every agent.  |
| `OPENAI_TEMPERATURE` | `0.2`                   | Sampling temperature.            |
| `CORS_ORIGINS`       | `http://localhost:3000` | Comma-separated allowed origins. |

Interactive API docs are available at `http://localhost:8000/docs`.

### 2. Frontend

```bash
cd frontend
npm install
npm start            # opens http://localhost:3000
```

The dev server proxies API calls to `http://localhost:8000` (configured via
`"proxy"` in `package.json`), so no extra config is needed for local dev. To
point at a different backend, set `REACT_APP_API_BASE_URL`.

## API

| Method | Path             | Description                                              |
| ------ | ---------------- | -------------------------------------------------------- |
| GET    | `/api/health`    | Liveness probe.                                          |
| GET    | `/api/languages` | Languages for the dropdown.                              |
| POST   | `/api/generate`  | Run the pipeline. Body: `{language, problem_statement}`. |

Example:

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"language":"python","problem_statement":"Validate an email address."}'
```

## Tests

```bash
cd backend
pip install pytest
pytest
```

The orchestrator tests inject fake agents, so they run without an API key or
network access.

## Supported languages

Python, JavaScript, TypeScript, Java, C, C++, C#, Go, Rust, Ruby, PHP, Kotlin,
and Swift. The list is defined once in `backend/app/schemas.py` (`Language`
enum) and served to the frontend via `/api/languages`.
