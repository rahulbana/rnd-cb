# AI Grammar & Rewriting Assistant

A Grammarly-like mini application powered by an LLM. Paste your text, pick a
transformation, and get a corrected/rewritten version with a **before/after
comparison** and a list of the individual changes.

## Features

- **Grammar correction** — fix grammar mistakes only
- **Spelling correction** — fix spelling & typos
- **Sentence improvement** — improve clarity and flow
- **Professional rewrite** — polished business tone
- **Simplification** — plain, easy-to-read language
- **Formal / informal conversion** — switch register
- **Before / after comparison** — side-by-side view plus a change list

### Example

**Before**
> I am not able to attend meeting because I have some urgent work.

**After**
> I won't be able to attend the meeting due to an urgent commitment.

## Tech stack

- **Backend:** Python 3.12, FastAPI, OpenAI SDK (structured JSON responses)
- **Frontend:** React + Vite
- **LLM:** OpenAI (`gpt-4o-mini` by default)

## Quick start

```bash
# 1. Install everything (creates a Python 3.12 virtualenv + installs deps)
./setup.sh

# 2. Add your OpenAI key
#    edit backend/.env and set OPENAI_API_KEY=sk-...

# 3. Run both servers
./start.sh
```

Then open **http://localhost:5173**.

- Frontend (Vite): http://localhost:5173
- Backend (FastAPI): http://127.0.0.1:8000
- Interactive API docs: http://127.0.0.1:8000/docs

## How it works

`setup.sh` creates a virtual environment at `backend/.venv` using
`python3.12`, installs the backend requirements and the frontend npm packages,
and copies `backend/.env.example` to `backend/.env`.

The backend exposes a single transformation endpoint:

```
POST /api/transform
{
  "text": "I am not able to attend meeting because I have some urgent work.",
  "action": "professional"
}
```

It returns structured JSON:

```json
{
  "action": "professional",
  "original": "…",
  "result": "…",
  "summary": "…",
  "changes": [
    { "original": "…", "replacement": "…", "reason": "…" }
  ]
}
```

Each action maps to a tailored prompt (see `backend/app/llm.py`). The model is
called with a low temperature and `response_format=json_object` for
**controlled, structured generation**, so the UI can render a reliable
before/after diff.

## Project layout

```
.
├── setup.sh                 # one-time setup (python3.12 venv + deps)
├── start.sh                 # runs backend + frontend together
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py          # FastAPI app + routes
│       ├── llm.py           # prompts + OpenAI call (structured output)
│       ├── schemas.py       # request/response models
│       └── config.py        # settings from env
└── frontend/
    ├── index.html
    ├── vite.config.js       # proxies /api -> backend
    └── src/
        ├── App.jsx          # UI + before/after comparison
        ├── api.js
        └── styles.css
```

## Configuration

Environment variables (in `backend/.env`):

| Variable          | Default        | Description                          |
| ----------------- | -------------- | ------------------------------------ |
| `OPENAI_API_KEY`  | *(required)*   | Your OpenAI API key                  |
| `OPENAI_MODEL`    | `gpt-4o-mini`  | Model to use                         |
| `OPENAI_BASE_URL` | *(unset)*      | Override for OpenAI-compatible hosts |
| `CORS_ORIGINS`    | localhost:5173 | Allowed CORS origins (comma-sep.)    |
