# factcheck — web-grounded fact-checking CLI agent

A command-line agent that takes any statement — a news headline, a universal
claim, a quote — searches the **live web** for evidence, and decides whether the
statement is **TRUE / FALSE / PARTIALLY TRUE / UNVERIFIED**, listing the sources
that support or refute it.

> **Core principle:** the language model is **not allowed to use its own
> memory** to judge the claim. It reasons *only* over text the agent gathered
> from the web during this run. If the gathered sources don't cover the claim,
> the verdict is forced to `UNVERIFIED`.

## How it works

```
claim ──▶ [1] draft search queries (LLM, language only)
       ──▶ [2] search the live web + fetch source text  (Tavily, "advanced"/deep search)
       ──▶ [3] verdict over gathered text ONLY           (OpenAI, evidence-bound prompt)
       ──▶ verdict + confidence + per-source stance + citations
```

The separation is deliberate:

- **Step 1** uses the LLM purely as a language tool to phrase good queries
  (including ones designed to *refute* the claim). It never judges truth here.
- **Step 2** is the only point that touches the open web. Its output is the
  sole evidence the verdict step ever sees.
- **Step 3** runs with `temperature=0` and a strict system prompt that forbids
  prior/parametric knowledge and requires every finding to cite a source index.

## Setup

```bash
pip install -r requirements.txt        # or: pip install -e .
cp .env.example .env                   # then fill in your keys
```

You need two keys:

| Variable           | Purpose                                            | Where |
|--------------------|----------------------------------------------------|-------|
| `OPENAI_API_KEY`   | Draft queries + reason over gathered text          | platform.openai.com |
| `TAVILY_API_KEY`   | Search the live web and fetch source content       | app.tavily.com (free tier) |
| `OPENAI_MODEL`     | *(optional)* model override, default `gpt-4o`      | — |

## Usage

```bash
# As a module
python -m factcheck "NASA confirmed water on the Moon's sunlit surface"

# Or, after `pip install -e .`
factcheck "The Great Wall of China is visible from space with the naked eye"

# Pipe a claim in
echo "Coffee was banned in Mecca in the 16th century" | factcheck

# Machine-readable output
factcheck --json "Bananas are technically berries" > result.json
```

### Options

| Flag                  | Default     | Description |
|-----------------------|-------------|-------------|
| `--model`             | `gpt-4o`    | OpenAI model to use. |
| `--max-queries`       | `4`         | How many search queries to generate. |
| `--results-per-query` | `5`         | Results requested per query. |
| `--max-sources`       | `12`        | Max sources passed to the verdict step. |
| `--depth`             | `advanced`  | Tavily search depth (`basic` or `advanced`). |
| `--json`              | off         | Emit the full report (claim, sources, verdict) as JSON. |

## Output

A color-coded verdict with a confidence score, a grounded conclusion, key
findings (each citing a source like `[2]`), and a table of every source with its
stance (`SUPPORTS` / `REFUTES` / `NEUTRAL`) and a one-line note.

## Project layout

```
factcheck/
  cli.py       # argparse entry point + stdin support
  agent.py     # pipeline orchestration
  llm.py       # query drafting + evidence-bound verdict (OpenAI)
  search.py    # web search + source gathering (Tavily) — the only web access
  models.py    # pydantic data structures
  output.py    # rich terminal rendering
  config.py    # settings / API key handling
```

## Limitations

- The verdict is only as good as the sources Tavily surfaces; obscure or very
  recent claims may come back `UNVERIFIED`.
- Source content is truncated per source before being sent to the model.
- This is a research aid, not an authority — always check the cited sources.
