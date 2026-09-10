# AI Product Description Generator

Generate structured e-commerce product descriptions from a simple product form,
powered by FastAPI + OpenAI on the backend and React (Vite) on the frontend.

Given a product name and a list of features, it produces a **Product Title**,
**Short Description**, **Detailed Description**, **Key Features**, **Benefits**,
**SEO Keywords**, and a **Meta Description** — all as structured JSON.

## Features

- **Product information form** — name, features, category, audience, seed keywords.
- **Multiple writing styles** — professional, casual, luxury, playful, technical, minimalist.
- **Short / long descriptions** — length control (short / medium / long).
- **SEO output** — keywords + a ≤160-char meta description.
- **Bullet-point features & benefits**.
- **Multiple variants** — generate up to 4 distinct versions at once.
- **Regenerate individual sections** — re-roll just the title, just the benefits, etc.

### Concepts demonstrated

Controlled generation (style/length knobs), prompt templates, structured output
(OpenAI JSON-schema response format + Pydantic), and content generation.

## Requirements

- **Python 3.12**
- **Node.js 18+** (for the frontend)
- An **OpenAI API key**

## Setup

```bash
./setup.sh
```

This creates a Python 3.12 virtual environment at `backend/.venv`, installs the
Python dependencies, runs `npm install` for the frontend, and creates
`backend/.env` from the example.

Then add your key to `backend/.env`:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini   # optional
```

## Run

```bash
./start.sh
```

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs

## Project structure

```
backend/
  app/
    main.py        # FastAPI routes
    models.py      # Pydantic request/response + structured output schema
    generator.py   # Prompt templates + OpenAI structured-output calls
    config.py      # Settings from .env
  requirements.txt
  .env.example
frontend/
  src/
    App.jsx        # Form + state
    ResultCard.jsx # Renders a variant with per-section regenerate
    api.js         # Backend client
    styles.css
setup.sh           # Creates the python3.12 venv and installs deps
start.sh           # Runs backend + frontend together
```

## API

| Method | Path                      | Purpose                                    |
| ------ | ------------------------- | ------------------------------------------ |
| GET    | `/api/health`             | Health + model/config status               |
| GET    | `/api/options`            | Available styles, lengths, section names   |
| POST   | `/api/generate`           | Generate one or more full variants         |
| POST   | `/api/regenerate-section` | Regenerate a single section of a variant   |
