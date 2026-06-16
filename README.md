# Resume Rater Agent

An AI agent that rates a resume against a job description and returns a
structured, quantitative assessment — overall score, per-dimension breakdown,
matched/missing skills, strengths, gaps, and concrete recommendations.

- **Frontend:** React (Vite)
- **Backend:** Python · FastAPI · OpenAI

## Architecture

```
frontend (React)  ──HTTP──>  backend (FastAPI)  ──>  OpenAI (structured JSON)
```

The backend exposes a small agent (`backend/agent.py`) that prompts an OpenAI
model with the resume + job description and forces a strict JSON schema
response, which is validated with Pydantic before being returned to the UI.

## Endpoints

| Method | Path             | Body                                            |
| ------ | ---------------- | ----------------------------------------------- |
| GET    | `/health`        | —                                               |
| POST   | `/api/rate`      | JSON `{ resume, job_description }`               |
| POST   | `/api/rate-file` | multipart: `resume_file` (PDF/txt), `job_description` |

## Backend setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then add your OPENAI_API_KEY
uvicorn main:app --reload     # serves on http://localhost:8000
```

Configuration (via `.env`):

- `OPENAI_API_KEY` — required.
- `OPENAI_MODEL` — defaults to `gpt-4o-mini`.
- `CORS_ORIGINS` — comma-separated allowed origins (defaults to the Vite dev server).

## Frontend setup

```bash
cd frontend
npm install
npm run dev                   # serves on http://localhost:5173
```

The Vite dev server proxies `/api` and `/health` to the backend on port 8000,
so no extra configuration is needed for local development.

## How scoring works

The agent evaluates four dimensions — Skills & Technologies, Experience,
Education & Certifications, and Achievements & Impact — and produces a holistic
overall score (0–100). All judgements are grounded strictly in the supplied
resume and job description.
