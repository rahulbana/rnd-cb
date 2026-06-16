# Ye'ai Assistant

A small CLI AI agent for the **Olympic Ye'ai** team, written in Python and
powered by an OpenAI LLM. You chat with it on the command line; behind the
scenes it decides when to call one of its built-in tools and uses the result to
answer you.

## Features / Tools

| Tool | What it does |
| --- | --- |
| `web_search` | Searches the web. `depth="normal"` returns top results (title, URL, snippet); `depth="deep"` also fetches and extracts the text of the top pages. |
| `convert_currency` | Live currency conversion, e.g. USD → GBP, GBP → USD. Accepts ISO codes or names ("dollar", "pound"). |
| `calculator` | Safe math: `+ - * / // % **`, plus `sqrt`, `square`, `cube`, `percent(a, b)`, and `sin/cos/tan/log/exp/factorial`. |
| `convert_length` | Length conversion, e.g. cm ↔ m, plus mm, km, inch, foot, yard, mile. |
| `country_summary` | Concise country facts: capital, region, population, area, currencies, languages, timezones, neighbours. |
| `time_and_weather` | Current local time, timezone (with UTC offset) and temperature for a country or city. |
| `summarize_webpage` | Fetch a web page by URL and extract its title + main readable text to summarize. |
| `summarize_youtube_video` | Fetch a YouTube video's transcript and metadata from its URL to summarize. |

The web search, currency, country, time/weather, webpage and YouTube tools use
free, **key-less** public APIs (DuckDuckGo, open.er-api.com, REST Countries,
Open-Meteo, YouTube oEmbed + `youtube-transcript-api`), so the only credential
you need is your OpenAI API key.

## Setup

```bash
# 1. Install dependencies (a virtualenv is recommended)
pip install -r requirements.txt

# 2. Configure your OpenAI key
cp .env.example .env
# then edit .env and set OPENAI_API_KEY (and optionally OPENAI_MODEL)
```

Configuration is read from environment variables (or `.env`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | _(required)_ | Your OpenAI API key. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model to use. |
| `OPENAI_BASE_URL` | _(unset)_ | Override the API base URL (Azure/proxy). |
| `YEAI_HTTP_TIMEOUT` | `20` | HTTP timeout (seconds) for tool API calls. |
| `YEAI_MAX_STEPS` | `8` | Max tool-calling rounds per question. |

## Usage

```bash
# Interactive chat
python -m yeai

# One-shot question
python -m yeai -q "Convert 50 US dollars to pounds"
python -m yeai -q "What is the square root of 1764, and 15% of 200?"
python -m yeai -q "What's the current time and temperature in Tokyo?"
python -m yeai -q "Summarize this video: https://youtu.be/dQw4w9WgXcQ"
python -m yeai -q "Summarize https://en.wikipedia.org/wiki/Olympic_Games"

# List the available tools
python -m yeai --list-tools
```

In the interactive REPL: `/tools` lists tools, `/reset` clears the
conversation, `/help` shows help, and `/exit` (or Ctrl-D) quits.

## Project layout

```
yeai/
  cli.py            # argparse + interactive REPL
  agent.py          # OpenAI chat loop with tool calling
  config.py         # env-based configuration
  tools/
    base.py         # Tool dataclass + registry
    http.py         # shared requests session
    search.py       # web_search (normal / deep)
    currency.py     # convert_currency
    calculator.py   # calculator (safe AST evaluator)
    units.py        # convert_length
    country.py      # country_summary
    time_weather.py # time_and_weather
    webpage.py      # summarize_webpage
    youtube.py      # summarize_youtube_video
tests/
  test_offline_tools.py
```

## Testing

```bash
pip install pytest
python -m pytest
```

The offline tests cover the calculator and unit conversion. The network-backed
tools are exercised live through the agent.

## Notes

This is an early, intentionally limited version. Each tool is self-contained and
registered through `yeai/tools/base.py`, so adding a new capability is just a
matter of defining a `Tool` and adding it to a module's `TOOLS` list.
