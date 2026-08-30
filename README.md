# 🥗 Diet Planner — Multi-Agent Application

A production-style, multi-agent application that takes a user's physical details
and goals and produces a personalized, safety-reviewed diet plan.

- **Backend:** Python · FastAPI · SQLAlchemy · SQLite · OpenAI SDK
- **Frontend:** React (Vite)
- **Orchestration:** a deterministic pipeline coordinating four specialized agents

---

## Architecture

```
                        ┌──────────────────────────────────────────────┐
  React frontend  ─────▶│  FastAPI  /api/v1/plans                       │
  (Vite dev proxy)      │      │                                        │
                        │      ▼                                        │
                        │  PlanService ──▶ Orchestrator (deterministic) │
                        │                     │                         │
                        │   1. IntakeAgent .......... validate/normalize│
                        │   2. NutritionAgent ....... BMR/TDEE/macros   │  ◀ pure Python
                        │   3. MealPlannerAgent ..... build meal plan   │  ◀ OpenAI LLM
                        │   4. SafetyAgent .......... rules + disclaimer│  ◀ rules + LLM
                        │                     │                         │
                        │                     ▼                         │
                        │              SQLite (diet_plans)              │
                        └──────────────────────────────────────────────┘
```

### Why this design

| Decision | Rationale |
|---|---|
| **Deterministic orchestrator** (plain function, not an autonomous agent) | The steps and their order are known. The simplest mechanism that solves the problem is easiest to test, observe, and reason about. |
| **Nutrition math is pure Python** | Calorie/macro targets must be correct and reproducible — never left to an LLM to guess. |
| **LLM only for meal planning + summaries** | Generative reasoning adds real value for variety and preferences; everything safety-critical stays deterministic (defense in depth). |
| **Graceful degradation** | With no `OPENAI_API_KEY`, a deterministic template planner keeps the app fully runnable and testable. The response's `meal_plan.source` records which path produced the plan. |
| **Safety agent can't be overruled by the model** | Hard rules (calorie floors, allergen leakage, calorie drift) are code; the LLM only writes the human-readable summary. |
| **SQLite + JSON documents** | Right-sized for this scale; promoted columns keep list/filter queries index-friendly. Swap `DATABASE_URL` to move to Postgres. |

---

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # optionally add OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

- API docs (Swagger): http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/v1/health

> Without an `OPENAI_API_KEY` the app runs in **fallback mode** — fully functional,
> using the deterministic template planner. Add a key for LLM-generated plans.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api to the backend)
```

---

## Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

Covers: nutrition math correctness (Mifflin–St Jeor reference values, calorie
floors, macro consistency), intake warnings, meal-planner fallback (allergen
exclusion, meal count), safety guardrails (allergen leak → not approved), the
orchestrator end-to-end, and the HTTP API (create/fetch/list/delete/validation)
— all with the LLM stubbed out, so no API key or network is required.

---

## API

| Method | Path | Description |
|---|---|---|
| `GET`  | `/api/v1/health` | Liveness + whether the LLM is enabled |
| `POST` | `/api/v1/plans` | Generate and store a diet plan |
| `GET`  | `/api/v1/plans` | List recent plans |
| `GET`  | `/api/v1/plans/{id}` | Fetch a stored plan |
| `DELETE` | `/api/v1/plans/{id}` | Delete a plan |

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/plans \
  -H 'Content-Type: application/json' \
  -d '{
    "age": 28, "sex": "female", "height_cm": 168, "weight_kg": 72,
    "activity_level": "light", "goal": "lose_weight",
    "diet_type": "vegetarian", "meals_per_day": 3,
    "allergies": ["nuts"], "dislikes": ["mushroom"]
  }'
```

---

## Configuration

All backend configuration is environment-driven (see `backend/.env.example`):
`OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_TIMEOUT_SECONDS`, `OPENAI_MAX_RETRIES`,
`DATABASE_URL`, `CORS_ORIGINS`, `LOG_LEVEL`, `APP_ENV`.

## Disclaimer

Generated plans are for **informational purposes only** and are not medical or
dietary advice. Consult a qualified professional before changing your diet.
