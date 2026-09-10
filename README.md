# AI JSON Generator

Convert natural language into **validated** JSON — with a custom schema, an
LLM-powered error-correction loop, download, and a REST API.

```
Input:                                Output:
  Create a customer named Rahul,        {
  email rahul@example.com,                "name": "Rahul",
  age 35,                                 "email": "rahul@example.com",
  and city Delhi.                         "age": 35,
                                          "city": "Delhi"
                                        }
```

This is a small but production-shaped example of **reliable structured
outputs** from an LLM — the pattern most GenAI systems depend on.

## Features

- **Natural-language input** → JSON
- **Custom JSON Schema** to constrain the output
- **JSON Schema validation** (Draft 2020-12, via `jsonschema`)
- **Error correction loop** — invalid output is fed back to the model with the
  exact validation errors and regenerated (up to N attempts)
- **Download / copy** the generated JSON
- **REST API** — use it without the UI

## Architecture

```
frontend/  React + Vite UI (calls the API, proxies /api -> :8000)
backend/   FastAPI + OpenAI
  app/
    main.py       API endpoints
    generator.py  generate -> validate -> correct loop
    validator.py  JSON Schema validation
    models.py     request/response schemas
    config.py     env-based settings
```

The reliability pattern lives in `backend/app/generator.py`:

1. Ask the model for JSON (JSON mode → always parseable).
2. Parse it; on failure, feed the parse error back and retry.
3. If a schema was supplied, validate against it.
4. On validation failure, send the **specific** errors back to the model and
   ask for a corrected value. Repeat up to `MAX_CORRECTION_ATTEMPTS` times.

## Requirements

- **Python 3.12**
- **Node.js 18+** (for the frontend)
- An **OpenAI API key**

## Setup

```bash
./setup.sh
```

This creates a Python 3.12 virtual environment at `backend/.venv`, installs
backend and frontend dependencies, and seeds `backend/.env` from the example.

Then add your key to `backend/.env`:

```
OPENAI_API_KEY=sk-...
```

## Run

```bash
./start.sh
```

- Frontend: http://localhost:5173
- Backend:  http://localhost:8000
- API docs: http://localhost:8000/docs

## API

### `POST /api/generate`

```bash
curl -s http://localhost:8000/api/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "Create a customer named Rahul, email rahul@example.com, age 35, city Delhi.",
    "schema": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "email": {"type": "string"},
        "age": {"type": "integer"},
        "city": {"type": "string"}
      },
      "required": ["name", "email", "age", "city"],
      "additionalProperties": false
    }
  }'
```

Response:

```json
{
  "data": { "name": "Rahul", "email": "rahul@example.com", "age": 35, "city": "Delhi" },
  "valid": true,
  "attempts": 1,
  "errors": [],
  "raw_output": "..."
}
```

`schema` is optional — omit it for freeform generation.

### `POST /api/validate`

Validate any JSON value against a schema (no LLM call):

```json
{ "data": { "age": "old" }, "schema": { "type": "object", "properties": { "age": { "type": "integer" } } } }
```

### `GET /api/health`

Reports status and whether an API key is configured.

## Tests

Offline validation tests (no API key needed):

```bash
cd backend
source .venv/bin/activate
python tests/test_validator.py
```

## Configuration

All optional, set in `backend/.env`:

| Variable                  | Default        | Description                          |
| ------------------------- | -------------- | ------------------------------------ |
| `OPENAI_API_KEY`          | —              | **Required** to generate             |
| `OPENAI_MODEL`            | `gpt-4o-mini`  | Model used for generation            |
| `OPENAI_BASE_URL`         | OpenAI default | For Azure/compatible gateways        |
| `OPENAI_TEMPERATURE`      | `0`            | Lower = more deterministic           |
| `MAX_CORRECTION_ATTEMPTS` | `3`            | Correction retries on invalid output |
| `CORS_ORIGINS`            | localhost:5173 | Comma-separated allowed origins      |
