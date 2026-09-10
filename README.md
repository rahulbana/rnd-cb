# AI Code Explainer

An AI tool that explains source code in simple, plain language. Paste code,
and the app can explain it, describe its functions and variables, find
potential bugs, generate documentation, add comments, and analyze its
complexity.

Built with **FastAPI** (backend), **React + Vite** (frontend), and the
**OpenAI** LLM API.

![Stack](https://img.shields.io/badge/stack-FastAPI%20%C2%B7%20React%20%C2%B7%20OpenAI-6d8bff)

## Features

- **Code editor** with syntax highlighting (Prism)
- **Automatic language detection** as you type
- **Explain code** — a plain-language, step-by-step walkthrough
- **Explain function** — purpose, parameters, return value, edge cases
- **Explain variables** — a table of each variable's type and role
- **Find potential bugs** — ranked findings with suggested fixes
- **Generate documentation** — overview, usage, and API reference
- **Add comments** — returns your code with helpful comments added
- **Complexity analysis** — Big-O for time and space, explained
- **Audience selector** — tailor explanations for beginner / intermediate / expert

## Requirements

- **Python 3.12**
- **Node.js 18+** and npm
- An **OpenAI API key**

## Setup

```bash
./setup.sh
```

This will:

1. Create a Python 3.12 virtual environment at `.venv`
2. Install backend dependencies from `backend/requirements.txt`
3. Install frontend dependencies (`npm install`)
4. Create `backend/.env` from the example

Then add your OpenAI key to `backend/.env`:

```
OPENAI_API_KEY=sk-...
```

## Run

```bash
./start.sh
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000 (docs at http://localhost:8000/docs)

The Vite dev server proxies `/api` calls to the backend, so you only need to
open the frontend URL.

## Project structure

```
.
├── backend/
│   ├── main.py            # FastAPI app and routes
│   ├── llm.py             # OpenAI client wrapper
│   ├── prompts.py         # Per-action prompt templates
│   ├── detect.py          # Language detection (Pygments + heuristics)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   └── components/    # CodeEditor, ResultPanel
│   ├── index.html
│   └── package.json
├── setup.sh               # One-time setup (creates venv, installs deps)
└── start.sh               # Launch backend + frontend
```

## API

| Method | Endpoint        | Description                                  |
| ------ | --------------- | -------------------------------------------- |
| GET    | `/api/health`   | Service status and whether the LLM is set up |
| GET    | `/api/actions`  | List of supported analysis actions           |
| POST   | `/api/detect`   | Detect the language of a snippet             |
| POST   | `/api/analyze`  | Run an analysis action on a snippet          |

### `POST /api/analyze`

```json
{
  "code": "def add(a, b):\n    return a + b",
  "action": "explain",
  "language": "Python",
  "audience": "beginner"
}
```

Valid `action` values: `explain`, `explain_function`, `explain_variables`,
`find_bugs`, `generate_docs`, `add_comments`, `complexity`.

## Configuration

Environment variables (set in `backend/.env`):

| Variable         | Default       | Description                        |
| ---------------- | ------------- | ---------------------------------- |
| `OPENAI_API_KEY` | _(required)_  | Your OpenAI API key                |
| `OPENAI_MODEL`   | `gpt-4o-mini` | Chat model to use                  |
| `CORS_ORIGINS`   | `*`           | Comma-separated allowed origins    |

## What you learn

Code-aware prompting, code analysis, and structured LLM responses.
