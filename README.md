# 📘 StudyForge — Multi-Agent Study Planner

An **agentic** application that designs personalised study plans for students in
**classes 5–12**, on **any subject and any topic**. A lead planner agent designs
the plan and **delegates** focused work to specialist agents that run in
parallel, then a lead coach assembles everything into one downloadable plan.

- **Frontend:** React + Vite (interactive, responsive, modern, lightweight)
- **Backend:** Python · FastAPI · LangGraph · LangChain · OpenAI
- **Download:** export any plan as **Markdown**, **JSON**, or **PDF** (print)

---

## 🧠 How the multi-agent system works

```
                ┌─────────────────────────────┐
   request ───▶ │  🧭 Lead Planner (delegates) │
                └──────────────┬──────────────┘
                               │  fan-out (parallel)
        ┌──────────────┬───────┴───────┬──────────────┐
        ▼              ▼               ▼              ▼
 📚 Curriculum   🗓️ Scheduler    🔗 Resources   ✅ Assessment
    Agent           Agent           Agent          Agent
        └──────────────┴───────┬───────┴──────────────┘
                               ▼
                ┌─────────────────────────────┐
                │  🧩 Lead Coach (compiler)    │ ──▶ final study plan
                └─────────────────────────────┘
```

- **Lead Planner** — builds the outline, goals, prerequisites and delegation briefs.
- **Curriculum Agent** — breaks the topic into progressive learning modules.
- **Scheduler Agent** — lays out a realistic week-by-week timetable.
- **Resources Agent** — curates videos, books, articles and exercises.
- **Assessment Agent** — designs assessments, practice sets and checkpoints.
- **Quiz Agent** — **researches the web** (CBSE/ICSE board sites, previous-year
  papers, teacher notes/quizzes) and then generates an abundant question bank:
  short answers, MCQs, multi-select MCQs (MMCQ), fill-in-the-blanks, true/false
  and long-answer questions — all with answers.
- **Lead Coach** — synthesises study tips and compiles the final plan.

Built with [LangGraph](https://langchain-ai.github.io/langgraph/) — the five
specialists fan out and run in parallel for speed. Progress streams live to the
UI over Server-Sent Events.

### 🔎 Web research for the quiz

Before writing questions, the Quiz Agent searches the web for board materials
and previous-year papers to match real exam patterns. It is **best-effort**: if
the network is unavailable or returns nothing, it falls back to the model's own
knowledge and quiz generation continues normally. Uses free DuckDuckGo search by
default, or [Tavily](https://tavily.com) when `TAVILY_API_KEY` is set. Disable
with `WEB_RESEARCH=false`.

---

## 🚀 Getting started

### 1. Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and set OPENAI_API_KEY=sk-...

uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (docs at `/docs`).

| Method | Endpoint                     | Purpose                                   |
| ------ | ---------------------------- | ----------------------------------------- |
| GET    | `/api/health`                | Health check + whether a key is configured |
| POST   | `/api/study-plan`            | Generate a plan (one-shot)                |
| POST   | `/api/study-plan/stream`     | Generate a plan with live agent progress (SSE) |
| POST   | `/api/study-plan/markdown`   | Re-render a plan to Markdown              |

### 2. Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The dev server proxies `/api` to the backend on
port 8000, so no extra configuration is needed.

---

## ⚙️ Configuration

Backend settings live in `backend/.env` (see `.env.example`):

| Variable         | Default        | Description                          |
| ---------------- | -------------- | ------------------------------------ |
| `OPENAI_API_KEY` | _(required)_   | Your OpenAI API key                  |
| `OPENAI_MODEL`   | `gpt-4o-mini`  | Model used by every agent            |
| `CORS_ORIGINS`   | localhost:5173 | Comma-separated allowed origins      |
| `WEB_RESEARCH`   | `true`         | Web research to ground quiz questions |
| `TAVILY_API_KEY` | _(optional)_   | Higher-quality research provider     |
| `RESEARCH_MAX_RESULTS` | `4`      | Results fetched per search query     |

---

## 📦 Project structure

The backend follows a layered, modular architecture:

```
backend/
  app/
    main.py                    # FastAPI application factory + lifespan
    core/                      # cross-cutting concerns
      config.py                #   typed settings (pydantic-settings)
      logging.py               #   logging configuration
      exceptions.py            #   AppError hierarchy (status + error_type)
    api/                       # HTTP layer
      router.py                #   aggregate /api router
      deps.py                  #   shared dependencies
      errors.py                #   exception handlers -> JSON envelopes
      routes/                  #   health, study_plans
    schemas/                   # pydantic models (request, content, quiz, plan)
    agents/                    # the multi-agent system
      registry.py              #   declarative agent registry (single source of truth)
      graph.py                 #   LangGraph wiring built from the registry
      prompts.py               #   all agent prompts in one place
      llm.py                   #   OpenAI client + structured-output runner
      state.py                 #   shared graph state
      nodes/                   #   one module per agent (+ timing decorator)
    services/
      planner_service.py       #   runs the graph (one-shot + SSE streaming)
      research.py              #   best-effort web research for the quiz
      exporters/               #   markdown, pdf, filename helpers
  tests/                       # pytest suite (offline, no API key needed)
  requirements.txt             # production dependencies
  requirements-dev.txt         # + test/dev dependencies
  pyproject.toml               # pytest & ruff configuration
frontend/
  src/
    App.jsx                    # orchestrates form → live agents → plan
    api.js                     # SSE client
    download.js                # Markdown / JSON / PDF download helpers
    components/                # form, agent timeline, plan view
    styles.css                 # modern, responsive, print-friendly styles
```

## 🧪 Tests

The backend ships with a pytest suite that exercises the whole agent graph,
API and exporters **offline** (the LLM and web research are stubbed, so no API
key or network is required):

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```
