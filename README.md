# 🧭 TravelPlanner — AI-Powered Multi-Agent Travel Companion

A production-grade, AI-native travel planning platform. Describe a trip in plain
language and a team of **13 specialised AI agents** research the destination,
build a realistic day-by-day itinerary, estimate a budget, check the weather,
and assemble everything the traveller needs — from visa notes to a packing list.

> **Runs with zero setup.** With no API keys the app runs fully **offline** using
> a deterministic mock LLM and estimate-based tools. Set `OPENAI_API_KEY` to
> unlock full AI reasoning. Every fact is labelled with its trust level, so
> estimates are never dressed up as live data.

---

## ✨ Highlights

| | |
|---|---|
| **Multi-agent architecture** | Orchestrator + 13 specialist agents, scheduled in dependency layers with parallel execution. No single "god prompt". |
| **Deterministic + LLM hybrid** | Keyword intent detection, a topological scheduler and deterministic scheduling/budget engines — the LLM does reasoning, not control flow. |
| **Data-trust model** | Every value carries provenance (`verified` / `live` / `estimated` / `ai_recommendation` / …). |
| **Structured outputs** | Agents return Pydantic-validated data; invalid model output falls back gracefully. |
| **Streaming** | Server-Sent Events stream safe planning progress (no chain-of-thought). |
| **Responsive UI** | Desktop multi-column dashboard → mobile single-column with bottom nav. Interactive itinerary, budget, map and a context-aware AI assistant. |
| **Runnable & tested** | FastAPI + SQLAlchemy, 31 passing tests, Docker Compose stack. |

---

## 🏗 Architecture

```
        Web / Mobile UI  (responsive SPA, served by FastAPI)
                 │  REST + SSE
        ┌────────▼────────┐
        │   FastAPI API   │  auth · trips · plan/stream · chat · destinations
        └────────┬────────┘
        ┌────────▼────────┐
        │  Travel         │  intent → dependency graph → parallel agents
        │  Orchestrator   │  → merge → synthesis
        └────────┬────────┘
   ┌─────────────┼───────────────────────────────┐
   ▼             ▼                                ▼
 Destination   Flight  Hotel  Itinerary  Budget  … (13 agents)
   │             │                                │
   └──────── Tool Registry (weather · geocode · currency · flight · search) ┘
                 │
     LLM layer: LLMProvider → ModelRouter → AgentRuntime (OpenAI | Mock)
                 │
        PostgreSQL (SQLite by default) · Redis (optional)
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full write-up.

---

## 🚀 Quick start

### Option A — one process (SQLite, offline)

```bash
git clone <repo> && cd rnd-cb
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload
# open http://127.0.0.1:8000
```

Or just run `./scripts/dev.sh`.

### Option B — full stack with Docker

```bash
cp .env.example .env          # optional; add OPENAI_API_KEY for full AI
docker compose up --build
# open http://127.0.0.1:8000
```

### Enable full AI

```bash
export OPENAI_API_KEY=sk-...
```

The app auto-detects the key and switches from the mock provider to OpenAI;
`GET /api/v1/meta` reports the active mode.

---

## 🖥 Using it

1. Open the app and type a request, e.g.
   *"Plan an 8-day trip to Tokyo from Delhi in October with my wife, budget 2.5 lakh, we love food, culture and photography."*
2. The request is parsed into structured requirements and the agents run with
   live progress.
3. Explore the **Overview, Itinerary, Budget, Map, Explore, Practical** tabs.
4. Ask the **Assistant** to *"make this trip cheaper"*, *"optimize my itinerary"*,
   or *"what can I do if it rains?"*.

---

## 🔌 API (v1)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/trips/parse` | NL → structured `TripRequest` |
| `POST` | `/api/v1/trips/from-text` | Create a trip from a prompt |
| `POST` | `/api/v1/trips` | Create from structured request |
| `GET`  | `/api/v1/trips` / `/{id}` | List / fetch |
| `POST` | `/api/v1/trips/{id}/plan` | Run the full multi-agent plan |
| `POST` | `/api/v1/trips/{id}/plan/stream` | Same, streamed via SSE |
| `POST` | `/api/v1/trips/{id}/optimize` | Re-run cost-sensitive agents |
| `GET/PATCH` | `/api/v1/trips/{id}/itinerary` | Read / reorder itinerary |
| `GET` | `/api/v1/trips/{id}/budget` `/weather` `/map` | Derived views |
| `POST` | `/api/v1/chat` `/chat/stream` | Context-aware assistant |
| `GET` | `/api/v1/destinations/{name}` | Ad-hoc destination research |
| `POST` | `/api/v1/auth/register` `/login`, `GET /auth/me` | Auth (JWT) |
| `GET` | `/api/v1/meta` `/health` | Mode, agents, tools, observability |

Interactive docs at `/docs` (Swagger) when the server is running.
Full reference: [`docs/API.md`](docs/API.md).

---

## 🧪 Tests

```bash
cd backend
pip install -r requirements.txt
pytest -q          # 31 tests, fully offline
```

Covers NL parsing, intent detection, tools, the orchestrator/agents and the
HTTP API end-to-end.

---

## 📚 Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system & component design
- [`docs/AGENTS.md`](docs/AGENTS.md) — every agent, its contract and tools
- [`docs/API.md`](docs/API.md) — REST reference
- [`docs/DATABASE.md`](docs/DATABASE.md) — persistence & the normalized model
- [`docs/SECURITY.md`](docs/SECURITY.md) — auth, isolation, prompt-injection defense
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) — project layout & how to extend

---

## 🗂 Project layout

```
backend/app/
  api/v1/        REST + SSE endpoints
  agents/        13 specialist agents + base
  orchestration/ intent, orchestrator (dependency layers), merge
  tools/         tool registry + weather/geocode/currency/flight/search
  llm/           LLMProvider, ModelRouter, AgentRuntime (OpenAI | Mock)
  schemas/       Pydantic contracts (trip state, agent I/O, data-trust)
  services/      trip / chat / NL parsing / engine singletons
  repositories/  data access (trips, users, observability)
  models/        SQLAlchemy tables + session
  security/      JWT auth + FastAPI deps
  config/        settings + logging
frontend/        responsive SPA (served by FastAPI)
infrastructure/  docker assets
docs/            architecture & guides
```

---

## 🌐 Live data sources

Real APIs are wired in behind the Tool Registry, with graceful fallback to
labelled estimates when a call fails or a key is missing. `ENABLE_LIVE_DATA`
(default `true`) is the master switch.

| Data | Provider | Key needed | Fallback |
|------|----------|-----------|----------|
| Geocoding | **Open-Meteo Geocoding** (worldwide) | none | 15-city gazetteer |
| Weather | **Open-Meteo** forecast/archive | none | seasonal climate table |
| Currency (FX) | **Frankfurter** (ECB rates) | none | static reference rates |
| Flights (distance/duration) | derived from real geocoding | none | — |
| Flights (real offers) | **Amadeus** | `AMADEUS_CLIENT_ID/SECRET` | distance estimate |
| Attractions & dining | **OpenTripMap** (OSM) | `OPENTRIPMAP_API_KEY` | LLM / heuristic |
| Web search | **Tavily** | `TAVILY_API_KEY` | none (honest empty) |
| Reasoning (agents/chat) | **OpenAI** | `OPENAI_API_KEY` | deterministic fallback |

The three keyless providers (geocoding, weather, currency) return **real data
out of the box** — no setup. Every value keeps its trust label (`live` /
`recent` / `estimated`), so the app never presents an estimate or an LLM guess
as a verified fact. See [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).
