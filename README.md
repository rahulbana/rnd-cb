# 🗓 Festival Date Agent

A small Python CLI that tells you **the exact date a festival was celebrated in
any year** — past or present. Forgot whether Diwali in 2025 was in October or
November? Need to know which day Eid al-Fitr fell on back in 1984? Ask the agent.

It uses an **OpenAI LLM** to compute dates for lunar / lunisolar festivals
(Diwali, Holi, Eid, Navratri, Easter, etc.), which shift on the Gregorian
calendar every year.

```
$ festival Diwali 1984
╭────────────────────── 🗓  Festival date ──────────────────────╮
│ Diwali — 1984                                                 │
│                                                               │
│ Date:       1984-11-13  (Tuesday)                             │
│ Full span:  11 Nov - 15 Nov 1984                              │
│ Confidence: high                                              │
│                                                               │
│ Diwali spans five days; the main day (Lakshmi Puja) is shown. │
╰───────────────────────────────────────────────────────────────╯
```

## Setup

```bash
pip install -r requirements.txt        # or: pip install -e .
cp .env.example .env                   # then add your OpenAI key
```

Set your key either in the `.env` file or the environment:

```bash
export OPENAI_API_KEY="sk-..."
```

## Usage

```bash
# Festival + year as positional arguments
festival Diwali 1984
festival "Eid al-Fitr" 2025

# Free-form question
festival --question "When did we celebrate Holi in 1995?"

# Raw JSON output (handy for scripts)
festival Diwali 1984 --json

# Interactive mode (just run with no arguments)
festival
```

If you haven't installed the console script, the same commands work via the
module:

```bash
python -m festival_agent Diwali 1984
```

## How it works

`festival_agent/agent.py` sends your question to an OpenAI model and forces a
**structured JSON response** (festival, ISO date, day of week, multi-day span,
confidence, and caveats). Structured output means the program always gets a
machine-readable date instead of a paragraph it would have to parse.

Islamic festivals historically depended on moon sighting and can vary by a day
across regions — the agent notes this and lowers its confidence accordingly.

## Configuration

| Variable                | Default       | Purpose                        |
| ----------------------- | ------------- | ------------------------------ |
| `OPENAI_API_KEY`        | _(required)_  | Your OpenAI API key.           |
| `FESTIVAL_AGENT_MODEL`  | `gpt-4o-mini` | Which OpenAI model to use.     |

## Tests

The tests run fully offline using a fake OpenAI client — no key or network
needed:

```bash
pip install pytest
pytest
```
