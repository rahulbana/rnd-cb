# Data sources & live APIs

Every external capability is a **Tool** behind the Tool Registry. Tools call
real APIs and fall back to labelled estimates on failure, so the app runs
whether or not it has network/keys. The trust label on each value always
reflects its true source (`live` / `recent` / `estimated` / `ai_recommendation`).

`ENABLE_LIVE_DATA` (default `true`) globally toggles live calls; set it `false`
to force fully-offline estimates.

## Keyless (real data out of the box)

| Tool | API | Notes |
|------|-----|-------|
| `geocode` | Open-Meteo Geocoding | Worldwide place → coordinates. Replaces the hardcoded gazetteer (still used as offline fallback). |
| `weather` | Open-Meteo Forecast / Archive | Dates ≤14 days → live forecast (`live`); further out → same-month historical average from the archive (`recent`); offline → seasonal table (`estimated`). |
| `currency` | Frankfurter (ECB) | Real FX rates; cached 6h. Static table fallback. |
| `flight_search` (distance) | — | Duration/price envelope from **real** great-circle distance via live geocoding, so it works for any city. Labelled `estimated`. |

## Behind a free key (opt-in)

| Tool | API | Env | Effect |
|------|-----|-----|--------|
| `flight_search` (offers) | Amadeus Self-Service | `AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET` | Resolves cities → IATA, fetches live flight offers (`live`). OAuth token cached. Falls back to the distance estimate. |
| `places` | OpenTripMap (OSM) | `OPENTRIPMAP_API_KEY` | Real named attractions & dining near the destination; feeds the activity/food agents (`live`). |
| `search` | Tavily | `TAVILY_API_KEY` | Real web search results (treated as **untrusted** content). |
| reasoning | OpenAI | `OPENAI_API_KEY` | Full agent reasoning + conversational chat. |

## Resilience

- `app/tools/http.py` is a shared async client with:
  - a **TTL cache** (Open-Meteo/FX responses cached hours–days),
  - a **negative cache** so one blocked/dead host doesn't slow a whole plan with
    repeated retries,
  - bounded retries with backoff, and it **never raises** — a failed call
    returns `None` and the tool falls back.
- Because of this, planning stays fast and complete even with no connectivity.

## Adding a provider

Implement `Tool.run` (see `app/tools/base.py`), call `get_json`/`post_json` from
`app/tools/http.py`, return `ToolResult` with the correct `trust`, and register
it in `app/tools/registry.py`. Prefer live data, always provide a fallback, and
never present external/LLM data as `verified`.
