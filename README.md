# product-intel — Multi-Agent Product Review & Feature Intelligence System

Turn a single product detail page + its customer reviews into a **prioritized
vNext product backlog**. A five-agent pipeline ingests reviews, clusters
sentiment by functional dimension, audits advertised features against reality,
diagnoses defects, and synthesizes a RICE-scored roadmap — emitted as JSON
(ready for a Jira/Linear import) and as an interactive HTML PM dashboard.

This is the reference implementation of the architecture in
`product_review_multi_agent_plan.pdf`. It runs **fully offline with zero
third-party dependencies** (Python standard library only), so it works in CI and
without any API key. Richer synthesis (Claude) and live browser scraping are
optional, lazily-imported extras.

## Architecture

```
[Product Detail URL]
        │
        ▼
┌─────────────────────────┐
│ Agent 1: Web Ingestion  │  scrape → clean → normalize → validate
└───────────┬─────────────┘
            │ IngestedProduct (metadata + reviews)
            ▼
┌─────────────────────────┐
│ Orchestrator / Director │  stateful graph, checkpointed
└───────────┬─────────────┘
   ┌────────┼─────────────────────────┐
   ▼        ▼                          ▼
Agent 2:   Agent 3:                  Agent 4:
Sentiment  Feature Audit             Problem & Defect
& Topic    (good vs. bad)           Diagnostics
   └────────┼─────────────────────────┘
            │ enriched insights + issues
            ▼
┌─────────────────────────┐
│ Agent 5: Roadmap &      │  RICE → P0/P1/P2 → tickets
│ Backlog Synthesis       │
└───────────┬─────────────┘
            ▼
[PM Dashboard + Prioritized vNext Backlog]
```

| Agent | Responsibility | Module |
|-------|----------------|--------|
| 1. Web Ingestion | DOM extraction, pagination, noise filtering, date/schema normalization | `agents/web_ingestion.py` |
| 2. Sentiment & Topic | Cluster reviews into functional dimensions, polarity distribution, filter courier/packaging noise | `agents/sentiment_topic.py` |
| 3. Feature Audit | Cross-examine advertised features vs. real sentiment → core strengths vs. expectation mismatches | `agents/feature_audit.py` |
| 4. Defect Diagnostics | Detect, dedupe, classify defects; frequency + severity weighting | `agents/defect_diagnostic.py` |
| 5. Roadmap Synthesis | RICE scoring, P0/P1/P2 priority, user stories + acceptance criteria + proposed actions | `agents/roadmap_synthesis.py` |

The **orchestrator** (`orchestrator.py`) wires these into the plan's topology
(sequential → fan-out at stage 3 → synthesis) with a lightweight, dependency-free
director. Every intermediate artifact is retained on `PipelineState` for
inspection and checkpointing.

## Install

Python 3.9+ (developed and tested on 3.12). Create and activate a virtual
environment first:

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
```

Then install the package (editable). The core pipeline pulls in **no**
third-party dependencies; add extras only for the optional integrations you use:

```bash
pip install -e .              # core pipeline, no dependencies
pip install -e '.[dev]'       # + pytest
pip install -e '.[anthropic]' # + Claude-backed synthesis
pip install -e '.[openai]'    # + OpenAI-backed synthesis
pip install -e '.[scraping]'  # + Playwright/BeautifulSoup live scraping
```

Combine extras in one go, e.g. `pip install -e '.[openai,dev]'`. To leave the
environment later, run `deactivate`.

Verify the install:

```bash
product-intel run --sample --html dashboard.html
pytest                             # if you installed the [dev] extra
```

## Usage

Three equivalent ways to invoke the CLI (use the underscore import name with
`python -m`; `python -m product-intel` with a hyphen is **not** valid):

```bash
product-intel run --sample                 # installed console script (simplest)
python -m product_intel run --sample       # module form
python -m product_intel.cli run --sample   # explicit module path
```

Run the bundled sample end-to-end and produce both outputs:

```bash
product-intel run --sample --json report.json --html dashboard.html
```

Analyze your own scraped payload (see the JSON shape in
`src/product_intel/fixtures/acousticpro_headphones.json`):

```bash
product-intel run --fixture my_product.json --html out.html
```

Use a hosted LLM for the reasoning/synthesis steps; each falls back to the
offline templates on any error:

```bash
product-intel run --sample --llm anthropic   # needs [anthropic] + ANTHROPIC_API_KEY
product-intel run --sample --llm openai       # needs [openai] + OPENAI_API_KEY
```

Override the model per provider via `ANTHROPIC_MODEL` / `OPENAI_MODEL`.

**API keys / `.env`:** copy `.env.example` to `.env` and fill in your key
(`cp .env.example .env`, then set `OPENAI_API_KEY=...`). The CLI auto-loads a
`.env` from the current directory (searching parents), so no extra tooling is
needed. Shell environment variables take precedence over the file, and
`--env-file PATH` points at a specific file. `.env` is git-ignored.

### Analyzing a real Amazon product

Live scraping is supported for **Amazon** URLs. Install the scraping extra first:

```bash
pip install -e '.[scraping]'
playwright install chromium
product-intel run --url "https://www.amazon.com/dp/B0XXXXXXXX" --live --html out.html
```

**Reality check:** Amazon aggressively blocks headless browsers (captcha /
"Robot Check") and gates many reviews behind login, so live scraping works
*sometimes* and fails *often*. The scraper detects the block and stops with a
clear message instead of returning garbage. Options when that happens:

* add `--no-headless` to show the browser window (dodges some blocks),
* cap volume with `--max-reviews N` (default 100),
* or — the reliable path — **save the page from your own browser** (right-click →
  *Save Page As* → "Web Page, Complete") and parse it offline, no anti-bot:

```bash
product-intel run --html-file product.html \
  --url "https://www.amazon.com/dp/B0XXXXXXXX" --html out.html
```

Both paths share one parser (`product_intel/scrapers/amazon.py`); only Amazon is
supported today. For other sites, save the page and adapt the parser, or supply a
`--fixture` JSON payload (see the sample schema).

`--strict-schema` emits only the plan's core output keys (omits the `diagnostics`
block). `--quiet` suppresses stage progress logs.

### Library API

```python
from product_intel import Orchestrator
from product_intel.agents.web_ingestion import FixtureScraper

report = Orchestrator(scraper=FixtureScraper(path="my_product.json")).run()
payload = report.to_dict()            # section-5 schema (+ diagnostics)
```

## Output schema

Top-level keys match section 5 of the plan exactly — `product_summary`,
`core_strengths`, `feature_gaps`, `vnext_backlog` — plus a `diagnostics` block
(clusters + defect log) used by the dashboard. Example:

```json
{
  "product_summary": { "product_id": "PROD-9842", "average_star_rating": 3.27, "...": "..." },
  "core_strengths":  [ { "feature": "Active Noise Cancellation", "sentiment_score": 0.9, "mention_frequency": 5 } ],
  "feature_gaps":    [ { "feature": "Multipoint Bluetooth Pairing", "sentiment_score": 0.25, "gap_description": "..." } ],
  "vnext_backlog":   [ { "ticket_id": "VNXT-101", "type": "Defect / Bug", "priority": "P0",
                         "title": "Bluetooth multipoint handoff disconnects",
                         "frequency_impact": "14.3% of all reviews", "proposed_action": "...",
                         "rice": { "reach": 14.3, "impact": 2.31, "confidence": 0.9, "effort": 2.0, "score": 11.56 },
                         "user_story": "...", "acceptance_criteria": ["..."] } ]
}
```

## Design notes: offline vs. production

The plan specifies dense embeddings, HDBSCAN/pgvector, LangGraph/CrewAI and
tiered LLM inference. To keep the reference pipeline runnable and testable
everywhere, this build uses deterministic, standard-library stand-ins behind
clean seams, so each can be swapped for its production counterpart without
touching the agents:

| Plan component | Reference stand-in | Swap point |
|----------------|--------------------|------------|
| Dense embeddings + HDBSCAN | Bag-of-words + cosine + threshold clustering | `nlp.py` |
| Topic classifier | Keyword taxonomy | `config.py` (`TOPIC_KEYWORDS`) |
| Tiered LLM inference | `OfflineLLM` templates / `AnthropicLLM` / `OpenAILLM` | `llm/` (implement `LLMClient`) |
| Playwright + anti-bot | `FixtureScraper` / `AmazonScraper` (Amazon live + saved-HTML) | `scrapers/amazon.py` |
| LangGraph/CrewAI | Lightweight `Orchestrator` | `orchestrator.py` |

The taxonomies and scoring weights in `config.py` are tuned for the sample
(audio/headphones); point at a different category by editing the keyword maps —
no agent code changes required.

## Tests

```bash
pytest
```

Covers the NLP primitives, each agent in isolation, and the end-to-end pipeline
against the plan's output schema.
