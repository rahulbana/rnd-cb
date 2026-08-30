# Architecture

## Overview

TravelPlanner is a layered, AI-native application. Requests flow from a
responsive SPA through a versioned REST/SSE API into a **Travel Orchestrator**
that coordinates specialised agents, which in turn use a **Tool Registry** and a
model-agnostic **LLM layer**.

```
UI ──REST/SSE──> FastAPI ──> Orchestrator ──> Agents ──> Tool Registry
                                   │                          │
                                   └── LLM layer ─────────────┘
                                          │
                              PostgreSQL / SQLite · Redis
```

## Layers

| Layer | Package | Responsibility |
|-------|---------|----------------|
| API | `app.api.v1` | HTTP contracts, validation, SSE streaming |
| Services | `app.services` | Application logic, NL parsing, orchestration entry |
| Orchestration | `app.orchestration` | Intent detection, dependency scheduling, merge, synthesis |
| Agents | `app.agents` | 13 single-purpose specialists |
| Tools | `app.tools` | External capabilities behind one registry |
| LLM | `app.llm` | Provider abstraction, model routing, structured outputs |
| Schemas | `app.schemas` | Pydantic contracts, incl. the data-trust model |
| Repositories | `app.repositories` | Data access |
| Models | `app.models` | SQLAlchemy tables + sessions |
| Security | `app.security` | JWT auth, dependencies, data isolation |

Each layer depends only on the ones below it, keeping components independently
testable.

## Orchestration (deterministic + LLM hybrid)

The LLM never controls flow. Control is deterministic:

1. **Intent detection** (`orchestration/intent.py`) — a keyword classifier maps
   the request to an intent with a confidence score.
2. **Agent selection** — single-topic intents map to one agent; `plan_trip`
   runs the full roster; `optimize` re-runs the cost-sensitive subset.
3. **Dependency layering** — `Orchestrator._layer()` runs a Kahn-style
   topological sort over each agent's `depends_on`, producing execution layers.
4. **Parallel execution** — agents within a layer run concurrently via
   `asyncio.gather`; results are merged deterministically after each layer.
5. **Merge** (`orchestration/merge.py`) — validated agent results are written
   into the shared `TripState`. Agents stay pure (no state mutation).
6. **Synthesis** — highlights are aggregated, conflicts detected (e.g. budget
   feasibility, itinerary-vs-duration), warnings de-duplicated.

```
plan_trip:
  layer 1 (parallel): destination, flight, hotel, activity, food, weather,
                      transportation, visa, safety, local_guide
  layer 2 (parallel): itinerary (needs activity+destination),
                      budget (needs activity+flight+hotel), packing (needs weather)
```

## LLM layer & cost control

`LLMProvider` is the single interface. `ModelRouter` picks a cheap model for
simple/moderate tasks and a stronger model for complex reasoning (section 30),
and selects the provider — **OpenAI** when a key is present, otherwise the
**mock** provider, so the system is always runnable.

`AgentRuntime.generate_structured()` asks the model for JSON matching a Pydantic
schema, validates it, and on any failure (invalid JSON, validation error,
network error) returns a caller-supplied **deterministic fallback**. This means:

- offline, agents produce valid structured data by construction;
- online, hallucinated/invalid output can never enter business logic unchecked.

## Data-trust model

`schemas/common.py::DataPoint[T]` wraps every externally-derived value with
`source`, `trust`, `freshness`, `confidence`, `retrieved_at`. Trust levels:
`verified · live · recent · estimated · ai_recommendation · user_provided`.
The UI renders these as coloured chips so users always know what they're looking
at.

## State

`TripState` (`schemas/trip.py`) is the single structured aggregate every agent
reads and the orchestrator writes — explicit fields per section, not an
unstructured conversation blob. It is persisted as a JSON document.

## Streaming

Planning emits `StreamEvent`s (`status`, `agent_started`, `agent_done`,
`result`, `done`) over SSE. Only safe progress/summaries are exposed — never
internal chain-of-thought.

## Error handling & resilience

- Tool calls are wrapped by the registry; failures return an error result, never
  an exception.
- Agent failures are caught in `BaseAgent.run` and reported as `FAILED` without
  crashing the plan.
- LLM calls retry with exponential backoff (`tenacity`) and degrade to fallbacks.

## Extensibility

Add an agent: implement `BaseAgent._run`, declare `depends_on`, register it in
`agents/__init__.py`, add a merge rule. The scheduler and API pick it up
automatically. Add a tool: implement `Tool.run`, register in
`tools/registry.py`. Swap a model: implement `LLMProvider`.
