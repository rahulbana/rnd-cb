# Agents

Every agent extends `BaseAgent` and implements `async _run(ctx) -> AgentResult`.
Agents are **stateless and pure**: they read `ctx.trip` (a `TripState`), may call
tools via `ctx.tools`, generate structured data via `ctx.runtime`, and return a
validated `AgentResult`. The orchestrator merges results into `TripState`.

## Contract

```python
class AgentResult(BaseModel):
    agent: str
    status: AgentStatus          # ok | partial | skipped | failed
    summary: str
    data: dict                   # validated structured payload
    citations: list[DataPoint]   # provenance
    warnings: list[str]
    latency_ms / tokens / cost_usd
```

`status = partial` signals degraded output (e.g. estimates or offline
fallbacks) — used heavily so the UI can be honest about data quality.

## Roster

| Agent | `depends_on` | Tools | Output schema |
|-------|--------------|-------|---------------|
| `destination` | — | — | `DestinationOverview` |
| `flight` | — | `flight_search` | `FlightOption` (Amadeus live or estimate) |
| `hotel` | — | — | hotel options |
| `activity` | — | `places` (OpenTripMap) | ranked `PlaceRec` list (real POIs when keyed) |
| `food` | — | `places` (OpenTripMap) | dining `PlaceRec` list (real POIs when keyed) |
| `weather` | — | `weather` | `WeatherOutlook` (never live-faked) |
| `transportation` | — | — | local transport modes |
| `visa` | — | — | `VisaInfo` (+ verify disclaimer) |
| `safety` | — | — | `SafetyInfo` (balanced) |
| `local_guide` | — | — | `LocalTips` |
| `itinerary` | `activity`, `destination` | — | deterministic day-by-day timeline |
| `budget` | `activity`, `flight`, `hotel` | `currency` | `BudgetBreakdown` (min/comfort/premium) |
| `packing` | `weather` | — | personalised list |

### Notable design choices

- **Itinerary is deterministic.** Rather than asking the LLM to invent a
  timetable (which risks impossible schedules), it slots the activities and
  dining the other agents produced into a realistic day template. Reliable and
  testable.
- **Budget is a deterministic engine.** It assembles min/comfort/premium tiers
  from flight/hotel/activity data and per-day category estimates, converts the
  USD flight estimate into the trip currency via the `currency` tool, and flags
  feasibility against the user's stated budget.
- **Flight & weather never fake live data.** They emit clearly-labelled
  `estimated` results with provenance.
- **Every agent has a deterministic fallback** so the whole system produces valid
  output offline.

## Adding an agent

1. Create `agents/my_agent.py` with a `BaseAgent` subclass.
2. Declare `depends_on` (agent names) if it needs other sections first.
3. Register it in `agents/__init__.py::ALL_AGENTS`.
4. Add a merge rule in `orchestration/merge.py`.
5. (Optional) map an intent to it in `orchestration/intent.py`.
