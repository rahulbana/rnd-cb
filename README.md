# Review Authenticity Crew 🕵️

A **multi-agent (CrewAI)** application in Python that checks the **authenticity and
reputation** of a product, restaurant, hotel, app, or service **before you spend
money or time on it**.

You give it a subject ("Bella Italia restaurant, Mumbai" or "Sony WH-1000XM5
headphones") and a crew of AI agents goes out, does a **deep web search**, reads
the reviews, and hands you back:

- ✅ **Top 5 best reviews** (with sources)
- ❌ **Top 5 worst reviews** (with sources)
- 👥 **How many people actually reviewed it** (total reviewer count)
- 🧭 **Overall sentiment + a 0–100 score**
- 📝 **A plain-English conclusion** (is it worth it?)
- 🔗 **All the sources** the report is based on
- 🛡️ **An authenticity assessment** from a dedicated verifier agent (are the
  reviews genuine? any fake/paid reviews? confidence level)

It is powered by **OpenAI** for the reasoning and **Tavily** (advanced "deep
search" mode) for the web research.

## How the multi-agent system works

The app runs three agents sequentially as a CrewAI *crew*:

| # | Agent | Role |
|---|-------|------|
| 1 | **Deep Researcher** | Runs deep Tavily searches across review platforms and collects real reviews + source URLs + reviewer counts. |
| 2 | **Sentiment Analyst** | Reads everything, scores the sentiment, and picks the top 5 positive & top 5 negative reviews with a conclusion. |
| 3 | **Verification Specialist** | Independently re-checks the claims and sources, flags fake/paid reviews, and produces the final, structured, trustworthy report. |

The final task returns a validated `ReviewReport` (Pydantic) so the output is
always well-structured.

```
[Deep Researcher] --deep search--> reviews + sources
        |
        v
[Sentiment Analyst] --> sentiment, top 5 best/worst, conclusion
        |
        v
[Verification Specialist] --re-search & verify--> FINAL VERIFIED REPORT
```

## Setup

```bash
# 1. (recommended) create a virtual environment
python -m venv .venv && source .venv/bin/activate

# 2. install dependencies
pip install -r requirements.txt

# 3. configure your API keys
cp .env.example .env
#   then edit .env and add OPENAI_API_KEY and TAVILY_API_KEY
```

Get the keys here:
- OpenAI: https://platform.openai.com/api-keys
- Tavily: https://app.tavily.com (free tier available)

## Usage

```bash
cd src

# pass the subject directly
python -m review_crew.main "Bella Italia restaurant, Bandra Mumbai" --type restaurant

# or for a product
python -m review_crew.main "Sony WH-1000XM5 headphones" --type product

# or run with no args and answer the prompts
python -m review_crew.main
```

### Example output (abbreviated)

```
======================================================================
 REVIEW AUTHENTICITY REPORT: Bella Italia restaurant (restaurant)
======================================================================
 Total reviewers found : 1243
 Overall sentiment     : Mostly Positive
 Positivity score      : 82.0/100

 CONCLUSION:
  Reliable choice for authentic Italian food; book ahead on weekends...

 TOP POSITIVE REVIEWS:
  1. (5/5) "Best carbonara in the city..."   source: https://...
  ...
 TOP NEGATIVE REVIEWS:
  1. (2/5) "Service was slow on a Friday night..."  source: https://...
  ...
 AUTHENTICITY ASSESSMENT (by verifier agent):
  Confidence: High. Reviews span Google, Tripadvisor and Zomato with
  consistent themes; no signs of coordinated fake reviews...

 SOURCES:
  - https://...
======================================================================
```

## Configuration

- **LLM model**: set `OPENAI_MODEL_NAME` in `.env` (default `gpt-4o`; use
  `gpt-4o-mini` for cheaper/faster runs).
- **Search depth**: the deep search tool always uses Tavily `search_depth="advanced"`.
- **Agents & tasks**: edit the prompts in `src/review_crew/config/agents.yaml` and
  `src/review_crew/config/tasks.yaml` — no code changes needed.

## Project layout

```
.
├── requirements.txt
├── .env.example
└── src/
    └── review_crew/
        ├── main.py                 # CLI entry point
        ├── crew.py                 # the 3-agent CrewAI crew
        ├── models.py               # ReviewReport structured output schema
        ├── tools/
        │   └── deep_search_tool.py # Tavily advanced/deep search tool
        └── config/
            ├── agents.yaml         # agent roles/goals/backstories
            └── tasks.yaml          # task descriptions/expected outputs
```
