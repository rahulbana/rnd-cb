# ✉️ AI Email Writer

Turn a one-line instruction into a polished, ready-to-send email. Choose the
email type, tone, and style; generate a subject and body; then rewrite, shorten,
or expand the draft until it's right.

Built with **FastAPI** (backend), **React + Vite** (frontend), and the
**OpenAI** API.

## Features

- **Intent → email** — describe what you want to say in plain language.
- **Email types** — request, follow-up, thank-you, apology, invitation, and more.
- **Tone control** — professional, friendly, formal, persuasive, empathetic, …
- **Style register** — professional / friendly / formal.
- **Subject + body** generated together as structured JSON.
- **Rewrite** with an optional extra instruction.
- **Shorten / Expand** while preserving tone and key points.
- Fully **editable** draft and one-click **copy**.

## Example

```
Input:
  Ask my manager for 2 days leave.

Output:
  Subject: Leave Request

  Hi John,
  I would like to request two days of leave...
```

## Project layout

```
backend/          FastAPI app
  main.py         API endpoints
  prompts.py      Prompt templates + tone/type/style vocabularies
  requirements.txt
  .env.example    Copy to .env and add your OpenAI key
frontend/         React + Vite single-page app
setup.sh          Install backend + frontend dependencies
start.sh          Run both servers together
```

## Quick start

```bash
./setup.sh                      # creates venv, installs deps, scaffolds .env
# add your key:
echo "OPENAI_API_KEY=sk-..." >> backend/.env   # or edit the file
./start.sh                      # starts backend (:8000) and frontend (:5173)
```

Then open <http://localhost:5173>.

> **Prerequisites:** Python 3.12 (recommended) and Node.js 18+. `setup.sh`
> prefers `python3.12` and falls back to `python3`.

## API

| Method | Path            | Purpose                                   |
| ------ | --------------- | ----------------------------------------- |
| GET    | `/health`       | Liveness + whether a key is configured    |
| GET    | `/api/options`  | Dropdown vocabularies (types/tones/styles)|
| POST   | `/api/generate` | Generate a new email from intent          |
| POST   | `/api/rewrite`  | Rewrite an existing email body            |
| POST   | `/api/transform`| Shorten or expand an existing email       |

Example:

```bash
curl -s localhost:8000/api/generate -H 'Content-Type: application/json' -d '{
  "intent": "Ask my manager for 2 days leave next week",
  "email_type": "request",
  "tone": "professional",
  "style": "professional",
  "recipient": "John",
  "sender": "Priya"
}'
```

## Configuration

`backend/.env` (see `.env.example`):

- `OPENAI_API_KEY` — required to generate emails.
- `OPENAI_MODEL` — defaults to `gpt-4o-mini`.
- `CORS_ORIGINS` — comma-separated allowed origins (defaults to the Vite dev server).
