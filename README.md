# 🎓 AI Question Generator

Turn any topic or study material into a graded quiz. Generate multiple-choice,
true/false, and short-answer questions at a chosen difficulty — each with an
answer and explanation — then take the quiz and get scored.

Built with **FastAPI** + **OpenAI** (structured JSON-schema output) on the
backend and **React** (Vite) on the frontend.

> Learning goals: structured generation, JSON schemas, evaluation, educational AI.

## Features

- **Input** any topic or paste study material
- **MCQ**, **True/False**, and **Short-answer** generation
- **Difficulty** selection (easy / medium / hard)
- **Answer + explanation** for every question
- **Quiz mode** with **score calculation** and per-question feedback
- **Structured generation** — the model is constrained to a JSON schema and
  every question is validated with Pydantic before it reaches the UI
- **Deterministic grading** — MCQ/TF by exact match, short-answer by keyword
  overlap (no extra LLM call), with unit tests

## Requirements

- **Python 3.12**
- **Node.js 18+** (for the React frontend)
- An **OpenAI API key**

## Setup

```bash
./setup.sh
```

`setup.sh` creates a Python 3.12 virtual environment in `.venv`, installs the
backend dependencies, copies `backend/.env.example` to `backend/.env`, and
installs the frontend dependencies.

Then add your OpenAI key:

```bash
# backend/.env
OPENAI_API_KEY=sk-...
```

> If your interpreter isn't `python3.12`, run `PYTHON=/path/to/python3.12 ./setup.sh`.

## Run

```bash
./start.sh
```

- Backend (API + docs): http://127.0.0.1:8000 — interactive docs at `/docs`
- Frontend: http://localhost:5173

The frontend proxies `/api/*` to the backend, so open the frontend URL and start
generating.

## Project layout

```
backend/
  app/
    main.py       # FastAPI app + routes
    schemas.py    # Pydantic models = JSON-schema contract for the LLM
    prompts.py    # System + user prompt construction
    llm.py        # OpenAI call with JSON-schema-constrained output
    grading.py    # Deterministic quiz scoring
    config.py     # Env-based settings
  tests/
    test_grading.py
  requirements.txt
frontend/
  src/
    App.jsx
    api.js
    components/GeneratorForm.jsx
    components/Quiz.jsx
setup.sh
start.sh
```

## API

| Method | Path            | Description                                   |
| ------ | --------------- | --------------------------------------------- |
| GET    | `/api/health`   | Health + whether OpenAI is configured         |
| POST   | `/api/generate` | Generate a question set from a topic          |
| POST   | `/api/grade`    | Grade submitted answers and return a score    |

Example generate request:

```json
{
  "topic": "Python Functions",
  "difficulty": "medium",
  "question_types": ["mcq", "true_false", "short_answer"],
  "num_questions": 5
}
```

## Tests

```bash
source .venv/bin/activate
cd backend && python -m pytest
```

The grading tests run without an OpenAI key.
