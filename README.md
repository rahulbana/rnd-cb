# rnd-cb — On This Day

A CLI agent that tells you **what important things happened on a given date**.
Type a date, and the agent uses an OpenAI model with **live web search** to dig
through websites, news archives and reference material, then writes up a
Markdown report and saves it.

It works two ways, detected automatically from your input:

| You type | Mode | What you get |
| --- | --- | --- |
| `7 July 1984` (has a year) | **Exact date** | Significant events, milestones, births & deaths on that specific day |
| `21 July` (no year) | **This day in history** | Notable events across *all* years that fell on that day — test matches, Olympic moments, celebrity birthdays, and more |

Coverage is worldwide with special attention to India, and you can emphasise any
country with `--country`.

Every report ends with a **Sources** section listing the exact pages the agents
used. And before anything is shown to you, a **second, independent verifier
agent** re-searches the web to fact-check the first agent's draft — correcting
errors and flagging anything it can't confirm.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env               # then put your key in .env (auto-loaded)
# ...or just: export OPENAI_API_KEY=sk-...
```

The entry point loads a local `.env` file automatically (via `python-dotenv`),
so `OPENAI_API_KEY` there is picked up without exporting it.

## Usage

```bash
# Exact date
python on_this_day.py 7 July 1984

# This day in history (no year)
python on_this_day.py 21 July

# Other accepted formats
python on_this_day.py 1969-07-20
python on_this_day.py 07/07/1984

# Emphasise a country, choose a model, control output
python on_this_day.py 26 January 1950 --country India
python on_this_day.py 21 July --model gpt-4o --output july21.md
python on_this_day.py 21 July --no-save

# Skip the fact-checking pass (faster / cheaper)
python on_this_day.py 21 July --no-verify

# Also produce a PDF (one section per page)
python on_this_day.py 21 July --pdf                 # -> reports/july-21.pdf
python on_this_day.py 7 July 1984 --pdf report.pdf  # custom path

# No arguments → it prompts you interactively
python on_this_day.py
```

Reports are saved to `./reports/<date>.md` by default (e.g.
`reports/1984-07-07.md` or `reports/july-21.md`).

### Options

| Flag | Description |
| --- | --- |
| `-c`, `--country` | Emphasise events for a particular country |
| `-m`, `--model` | OpenAI model (default: `$OPENAI_MODEL` or `gpt-4o`) |
| `-o`, `--output` | Path to save the Markdown report |
| `--no-save` | Do not save the Markdown report |
| `--pdf [PATH]` | Also save a sectioned PDF (one section per page); default `reports/<date>.pdf` |
| `--no-verify` | Skip the independent fact-checking pass |
| `--version` | Show version |

## How it works

It's a two-agent pipeline:

1. **`history_agent/dateparse.py`** — parses your free-form date and decides
   whether a year was supplied (exact-date vs. this-day-in-history mode).
2. **`history_agent/agent.py`**
   - **Agent 1 — Researcher:** calls the OpenAI **Responses API** with the
     built-in `web_search` tool so the model genuinely browses the internet, and
     drafts a structured report with a mandatory **Sources** section.
   - **Agent 2 — Verifier:** a *separate* fact-checking agent independently
     re-searches the web to confirm or correct each claim, flags anything it
     can't verify, and consolidates the source list. (Skip with `--no-verify`.)
3. **`history_agent/pdf.py`** — renders the final report to a PDF with **one
   section per page** (each `##` heading starts a new page), styled headings,
   bullet/numbered lists, clickable source links and page numbers.
4. **`history_agent/cli.py`** — the command-line interface; reports progress and
   saves the final, verified report (Markdown, and PDF with `--pdf`).

## Development

```bash
python -m unittest discover -s tests -v
```

The date-parsing tests run offline (no API key needed).
