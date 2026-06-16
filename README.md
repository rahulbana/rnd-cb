# rnd-cb — Board Exam Question-Paper Agent

A **multi-agent system** that finds and downloads board examination question
papers (CBSE, ICSE/CISCE, UP Board, and other Indian state boards) for a given
**subject** (English, Hindi, Mathematics, …) and **class** (10th, 12th, …).

It is powered by an **OpenAI LLM** and built as four cooperating agents that run
in a strict pipeline:

```
  ┌───────────┐   ┌────────────┐   ┌─────────────┐   ┌──────────────┐
  │  Planner  │ → │  Searcher  │ → │  Validator  │ → │  Downloader  │
  └───────────┘   └────────────┘   └─────────────┘   └──────────────┘
   make a plan     search the web    check the data    download files
```

1. **PlannerAgent** — turns your request into a precise search plan: queries to
   run, trusted sources (official board sites, reputable portals), and
   acceptance criteria.
2. **SearchAgent** — uses the LLM's **web search** tool to find candidate papers
   with direct links.
3. **ValidatorAgent** — checks every candidate against the request (correct
   board, subject, class, plausible year, actually a question paper) and assigns
   a confidence score. Only papers above the confidence threshold pass.
4. **DownloaderAgent** — downloads the validated papers to disk and writes a
   `manifest.json` describing the run.

The [`Orchestrator`](qpaper_agent/orchestrator.py) wires the four agents together
and enforces overall policy (paper count, confidence threshold, dry-run).

## Install

```bash
pip install -r requirements.txt
cp .env.example .env          # then add your OpenAI API key
```

Set your key (either in `.env` or the environment):

```bash
export OPENAI_API_KEY=sk-...
```

## Usage

```bash
# CBSE Class 10 English, recent years
python -m qpaper_agent --board CBSE --class 10 --subject English

# UP Board Class 12 Hindi, specific years, at most 8 papers
python -m qpaper_agent --board "UP Board" --class 12 --subject Hindi \
    --years 2022 2023 2024 --max 8

# ICSE Class 10 Mathematics — plan + search + validate only, no download
python -m qpaper_agent --board ICSE --class 10 --subject Mathematics --dry-run
```

### Options

| Flag | Description | Default |
| --- | --- | --- |
| `--board` | Board: CBSE, ICSE, UP Board, … | *(required)* |
| `--class` | Class / grade, e.g. `10`, `12` | *(required)* |
| `--subject` | Subject, e.g. English, Hindi | *(required)* |
| `--paper-type` | previous year / sample / model … | `previous year question papers` |
| `--years` | Specific years (space-separated) | recent years |
| `--max` | Max papers to download | `10` |
| `--min-confidence` | Validator acceptance threshold (0–1) | `0.5` |
| `--output-dir` | Where to save papers | `downloads/` |
| `--dry-run` | Skip the actual download step | off |

Downloaded papers and the run manifest land in
`downloads/<board>_class<n>_<subject>/`.

### Use it as a library

```python
from qpaper_agent import Orchestrator, PaperRequest

report = Orchestrator().run(
    PaperRequest(board="CBSE", subject="English", klass="10", max_papers=5)
)
print(report.to_dict()["summary"])
```

## Configuration

All settings have sensible defaults and can be overridden via environment
variables (see [`.env.example`](.env.example)):

| Variable | Purpose | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | OpenAI API key (**required**) | — |
| `QPAPER_MODEL` | Model for planning & validation | `gpt-4o` |
| `QPAPER_SEARCH_MODEL` | Model for web search | `gpt-4o` |
| `QPAPER_OUTPUT_DIR` | Output directory | `downloads` |
| `QPAPER_HTTP_TIMEOUT` | Download timeout (s) | `60` |
| `QPAPER_MAX_CANDIDATES` | Candidate cap between stages | `25` |

## Project layout

```
qpaper_agent/
  config.py         settings loaded from env / .env
  models.py         pydantic models shared across agents (also LLM schemas)
  llm.py            OpenAI client wrapper (structured output + web search)
  orchestrator.py   coordinates the four-stage pipeline, writes the manifest
  cli.py            command-line entrypoint (python -m qpaper_agent)
  agents/
    planner.py      stage 1 — build the search plan
    searcher.py     stage 2 — web search for candidates
    validator.py    stage 3 — verify candidates match the request
    downloader.py   stage 4 — download files to disk
tests/
  test_smoke.py     offline tests (no API key / network needed)
```

## Tests

```bash
python -m pytest tests/ -v
```

The smoke tests cover the pure-Python pieces (models, slugging, dry-run
downloader, config) and need neither network nor an API key.

## Notes & responsible use

- The search and validation stages are LLM-driven and depend on what is publicly
  available on the web at run time; always sanity-check the results.
- Only download papers you are permitted to access, and respect the terms of the
  hosting sites. The validator rejects obvious non-papers, but it is an aid, not
  a guarantee.
