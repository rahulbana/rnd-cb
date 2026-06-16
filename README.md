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

## Setup

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...        # or copy .env.example to .env
```

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
| `--no-save` | Print the report without saving |
| `--version` | Show version |

## How it works

1. **`history_agent/dateparse.py`** — parses your free-form date and decides
   whether a year was supplied (exact-date vs. this-day-in-history mode).
2. **`history_agent/agent.py`** — calls the OpenAI **Responses API** with the
   built-in `web_search` tool so the model genuinely browses the internet, then
   returns a structured Markdown report with a Sources section.
3. **`history_agent/cli.py`** — the command-line interface; saves the report.

## Development

```bash
python -m unittest discover -s tests -v
```

The date-parsing tests run offline (no API key needed).
