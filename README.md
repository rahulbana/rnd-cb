# ✍️ AI Blog Generator

An AI-powered blog creation platform built with **FastAPI**, **React**, and the
**OpenAI** API. It turns a short brief (topic, audience, style, length) into a
complete, well-structured article using **multi-step prompting and prompt
chaining**.

## What it does

Give it a topic and it walks the classic content workflow:

```
Topic  →  Outline  →  Introduction → Section 1 → Section 2 → … → Conclusion
```

Core features:

- **Topic input** with **target audience**, **writing style**, and **article length**
- **Generate outline** — a logically ordered structure
- **Generate sections** — one at a time, or all at once, kept coherent via the outline
- **Generate complete article** — chains every step in one click
- **Generate title** — several click-worthy options to choose from
- **Generate meta description** — SEO-ready, ≤155 characters
- **Rewrite sections** — refine any section with a custom instruction

This project demonstrates: multi-step prompting, content generation, prompt
chaining, and structured workflows.

## Architecture

```
rnd-cb/
├── backend/                 # FastAPI + OpenAI
│   ├── app/
│   │   ├── main.py          # FastAPI app + CORS + /api/health
│   │   ├── config.py        # env-based settings
│   │   ├── schemas.py       # request/response models
│   │   ├── routers/
│   │   │   └── generate.py  # /api/outline, /section, /article, /title, ...
│   │   └── services/
│   │       └── llm.py       # prompt chaining lives here
│   └── requirements.txt
├── frontend/                # React + Vite
│   └── src/
│       ├── App.jsx          # the workflow UI
│       ├── api.js           # backend client
│       └── components/
├── setup.sh                 # create venv (Python 3.12) + install deps
└── start.sh                 # run backend + frontend together
```

## Requirements

- **Python 3.12**
- **Node.js 18+** and **npm**
- An **OpenAI API key**

## Setup

```bash
./setup.sh
```

This creates a Python 3.12 virtual environment at `backend/.venv`, installs the
backend and frontend dependencies, and creates `backend/.env` from the example.

Then add your OpenAI key:

```bash
# edit backend/.env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini      # optional, this is the default
```

## Run

```bash
./start.sh
```

- Frontend: http://localhost:5173
- Backend API + interactive docs: http://localhost:8000/docs

Press `Ctrl+C` to stop both.

## API overview

All endpoints are `POST` (except health) and accept the brief fields
`topic`, `audience`, `style`, `length` (`short` | `medium` | `long`).

| Endpoint                  | Purpose                                  |
| ------------------------- | ---------------------------------------- |
| `GET  /api/health`        | Status + whether an OpenAI key is set    |
| `POST /api/outline`       | Generate an outline                      |
| `POST /api/section`       | Write one section (takes `heading`)      |
| `POST /api/article`       | Full article via prompt chaining         |
| `POST /api/title`         | Suggest titles                           |
| `POST /api/meta-description` | Generate an SEO meta description      |
| `POST /api/rewrite`       | Rewrite a section (takes `content`, `instruction`) |

Example:

```bash
curl -X POST http://localhost:8000/api/outline \
  -H "Content-Type: application/json" \
  -d '{"topic":"Generative AI for Beginners","audience":"beginners","style":"friendly","length":"medium"}'
```
