# API reference (v1)

Base path: `/api/v1`. Interactive docs: `/docs` (Swagger UI), `/redoc`.

Authentication is **optional**. Anonymous callers share unowned trips; a valid
`Authorization: Bearer <token>` scopes trips to the authenticated user.

## System

- `GET /health` → `{status, app}`
- `GET /meta` → active LLM mode, agent list, tool list, observability summary.

## Auth

- `POST /auth/register` `{email, password, full_name?}` → `{access_token}`
- `POST /auth/login` `{email, password}` → `{access_token}`
- `GET /auth/me` → current user (requires bearer)
- `PATCH /auth/me/preferences` `{preferences}` → user

## Trips

- `POST /trips/parse` `{text}` → `TripRequest` (NL → structured, no persistence)
- `POST /trips/from-text` `{text}` → `TripState` (parse + create)
- `POST /trips` `TripCreate` → `TripState`
- `GET /trips` → `TripSummary[]`
- `GET /trips/{id}` → `TripState`
- `PATCH /trips/{id}` `{title?, request?}` → `TripState`
- `DELETE /trips/{id}` → 204 (soft delete)

## Planning

- `POST /trips/{id}/plan` → `TripState` (runs all agents)
- `POST /trips/{id}/plan/stream` → `text/event-stream` of `StreamEvent`
- `POST /trips/{id}/optimize` → `TripState` (re-runs activity/budget/itinerary)
- `GET /trips/{id}/itinerary` → `ItineraryDay[]`
- `PATCH /trips/{id}/itinerary` `{itinerary}` → persists a reordered plan
- `GET /trips/{id}/budget` → `BudgetBreakdown`
- `GET /trips/{id}/weather` → weather outlook
- `GET /trips/{id}/map` → `{center, points[]}` geocoded

## Chat

- `POST /chat` `{trip_id?, message, history?}` → `{reply, intent, used_agents, suggestions}`
- `POST /chat/stream` → SSE token stream then a `result` event

## Destinations

- `GET /destinations/{name}` → ad-hoc overview/weather/safety/local tips

## SSE event shape

```json
{ "type": "agent_done", "agent": "budget", "message": "Comfort budget ~…", "data": {"status": "ok"} }
```

`type` ∈ `status | agent_started | agent_done | token | result | error | done`.
The final `result` event carries the full `TripState`; `done` closes the stream.

## Example

```bash
curl -X POST localhost:8000/api/v1/trips/from-text \
  -H 'content-type: application/json' \
  -d '{"text":"8 day trip to Tokyo from Delhi in October, budget 2.5 lakh, love food and photography"}'

curl -N -X POST localhost:8000/api/v1/trips/<id>/plan/stream   # streamed progress
```
