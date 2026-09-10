# AI Meeting Notes Generator

Turn a raw meeting transcript into structured, useful notes using an LLM:

- **Summary** of the meeting
- **Participants** identified
- **Decisions** made
- **Action items** with owners
- **Deadlines** to track
- A ready-to-send **follow-up email**

```
Meeting Transcript
        ↓
      LLM  (OpenAI, structured output)
        ↓
 ┌─────────────────┐
 │ Summary         │
 │ Decisions       │
 │ Action Items    │
 │ Owners          │
 │ Deadlines       │
 │ Follow-up email │
 └─────────────────┘
```

## Stack

- **Backend:** Python 3.12 + FastAPI, OpenAI structured output (`response_format` → Pydantic).
- **Frontend:** React + Vite.

## Setup

Requires `python3.12` and `node` on your PATH.

```bash
./setup.sh
```

This creates a virtual environment at `backend/.venv`, installs backend and
frontend dependencies, and bootstraps `backend/.env` from the template.

Then add your OpenAI API key to `backend/.env`:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

## Run

```bash
./start.sh
```

- Frontend: http://localhost:5173
- Backend API + docs: http://localhost:8000/docs

Open the frontend, paste a transcript (or click **Load sample** / **Upload .txt**),
and click **Generate notes**.

## API

| Method | Path            | Description                                   |
| ------ | --------------- | --------------------------------------------- |
| GET    | `/api/health`   | Health check + model/config status.           |
| POST   | `/api/upload`   | Upload a `.txt`/`.md` file, returns its text.  |
| POST   | `/api/generate` | Generate structured notes from a transcript.  |

`POST /api/generate` body:

```json
{ "transcript": "…", "meeting_title": "optional" }
```

## Project layout

```
backend/
  app/
    main.py          FastAPI app + routes
    config.py        Settings (.env)
    models.py        Pydantic schemas (structured output)
    services/llm.py  OpenAI call
  requirements.txt
frontend/
  src/
    App.jsx                    Upload + transcript input
    components/NotesDisplay.jsx Results view
    api.js                     Backend client
setup.sh
start.sh
```
