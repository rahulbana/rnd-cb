# Development guide

## Prerequisites
- Python 3.11+ (3.12 recommended)
- (Optional) Docker + Docker Compose for the full stack

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload
```

App at http://127.0.0.1:8000 — the FastAPI process also serves the SPA from
`frontend/`.

## Run tests

```bash
cd backend && pytest -q
```

Tests run fully offline against an isolated temp SQLite DB (see
`tests/conftest.py`). `asyncio_mode = auto` is set in `pyproject.toml`.

## Project layout

```
backend/app/
  main.py            app factory, CORS, middleware, static mount
  config/            settings (pydantic-settings) + logging
  schemas/           Pydantic contracts (common/trip/agents/chat)
  llm/               base · mock_provider · openai_provider · router · runtime
  tools/             registry + weather/geocode/currency/flights/search
  agents/            base + 13 specialists + _common helpers
  orchestration/     intent · orchestrator · merge
  services/          engine · nlp · trip_service · chat_service
  repositories/      trip / user / observability
  models/            db (engine/session) · tables (ORM)
  security/          auth · deps
  api/v1/            health · auth · trips · planning · chat · destinations
frontend/            index.html · styles.css · app.js (no build step)
```

## Common tasks

**Add an agent** → see [`AGENTS.md`](AGENTS.md#adding-an-agent).

**Add a tool**
```python
# app/tools/my_tool.py
class MyTool(Tool):
    name = "my_tool"
    async def run(self, **kwargs): return self._ok(...)
# register in tools/registry.py::build_default_registry
```

**Add an endpoint** → create a router in `api/v1/`, include it in
`api/v1/__init__.py`.

**Swap the model provider** → implement `LLMProvider` and return it from
`ModelRouter._build_provider`.

## Conventions
- Type hints everywhere; Pydantic v2 for I/O.
- Agents are pure; only the orchestrator mutates `TripState` (via `merge`).
- Never present estimates/LLM output as verified facts — wrap values in
  `DataPoint` with the right `trust`.
- Async for I/O-bound work; agents in a layer run concurrently.

## Style
`ruff` config lives in `backend/pyproject.toml` (line length 110). Run
`ruff check backend/app` if installed.
