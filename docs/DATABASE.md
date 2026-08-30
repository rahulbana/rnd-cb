# Database

Default: **SQLite** (zero-config). Production: **PostgreSQL** via `DATABASE_URL`
(`postgresql+psycopg://…`). The ORM models are database-agnostic. Schema is
created on startup via `init_db()`; production should use Alembic migrations.

## Implemented tables

| Table | Purpose |
|-------|---------|
| `users` | account, hashed password (pbkdf2_sha256), JSON `preferences`, `is_active`, timestamps |
| `trips` | the `TripState` aggregate stored as a JSON document (`state`), `status`, `is_deleted` (soft delete), `user_id` FK |
| `agent_runs` | one row per agent execution — `run_id`, `agent_name`, `status`, `model`, `latency_ms`, `tokens`, `cost_usd`, `error` (observability, section 29) |
| `tool_calls` | tool invocations with `trust` + latency |

UUID primary keys, foreign keys, indexes on lookup columns, soft deletion on
trips, created/updated timestamps.

## Why a JSON aggregate for trips?

`TripState` is a rich, evolving aggregate that is always read and written as a
whole. Persisting it as one JSON document keeps the domain model authoritative
and avoids brittle multi-table syncing during rapid iteration, while
`agent_runs`/`tool_calls` give the relational observability surface that
analytics need.

## Normalized model (reference / roadmap)

For heavy analytical querying the spec's normalized schema (section 22) maps
cleanly onto `TripState`:

```
users ─< trips ─< itineraries ─< itinerary_items
                 ├─< accommodations
                 ├─< flights
                 ├─< activities
                 ├─< restaurants
                 ├─< transportation
                 ├─< budgets ─< budget_lines
                 └─< documents (visa/safety/local)
trips ─< trip_members
trips ─< agent_runs ─< tool_calls
users ─ user_preferences (1:1)
```

Each `TripState` section corresponds to one of these tables; a migration would
project the document into columns. `agent_runs`/`tool_calls` are already
normalized here.

## Switching to PostgreSQL

```bash
export DATABASE_URL=postgresql+psycopg://travel:travel@localhost:5432/travelplanner
```

`docker compose up` provisions Postgres + Redis and points the backend at them.
