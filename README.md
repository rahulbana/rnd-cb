# Code Review Agent

A production-grade, LLM-powered **code review CLI** built on the OpenAI API.
It reviews a **single file** or an **entire directory** and reports concerns
across multiple perspectives — **security**, **data types**, **harmful code**,
performance, error handling and best practices — as structured JSON.

## Features

- **File or directory** review — point it at one file or a whole tree.
- **Language-aware** collection — filters directory scans by language extension.
- **Multi-perspective analysis** — security, data types, harmful code, and more
  (the perspective list is data-driven and easy to extend).
- **Structured, machine-readable output** — strict JSON schema, plus a
  human-friendly console view.
- **Enterprise-ready** — concurrency, retry with exponential backoff,
  per-file fault isolation, file-size guards, CI-friendly exit codes, and
  support for OpenAI-compatible / Azure gateways.
- **Keys from `.env`** — credentials never live in code.

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .            # installs the `code-review` command
```

## Configuration

Copy `.env.example` to `.env` and add your key:

```bash
cp .env.example .env
# then edit .env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Any value can also be supplied as a normal environment variable; existing
process env vars take precedence over the `.env` file.

## Usage

```bash
# Review a single file
code-review path/to/file.py python

# Review every Python file in a directory
code-review path/to/project python

# Human-friendly console view
code-review src/ javascript --format pretty

# Full report (per-file findings + summary) written to a file
code-review src/ go --format json --output report.json

# CI mode: non-zero exit if any issue is found
code-review src/ python --fail-on-issues
```

Positional arguments are **`path`** and **`language`**, exactly as requested.

### Options

| Flag | Description |
|------|-------------|
| `-f, --format {review,json,pretty}` | Output format (default `review`). |
| `-o, --output FILE` | Write output to a file instead of stdout. |
| `-m, --model MODEL` | Override the model (else `OPENAI_MODEL`). |
| `-c, --concurrency N` | Files reviewed in parallel. |
| `--env-file PATH` | Explicit `.env` location. |
| `--no-color` | Disable ANSI colours in `pretty` output. |
| `--fail-on-issues` | Exit `1` if any issue is found (for CI). |
| `-v, --verbose` | Verbose logging to stderr. |

You can also run it as a module: `python -m code_review_agent <path> <language>`.

## Output format

The default `review` format matches the requested contract. For a **single
file** it is the review object directly:

```json
{
  "security":     {"status": 1, "severity": "critical", "explanation": "...", "suggestion": "..."},
  "data_type":    {"status": 0, "severity": "none",     "explanation": "...", "suggestion": ""},
  "harmful_code": {"status": 1, "severity": "high",     "explanation": "...", "suggestion": "..."},
  "performance":    {"status": 0, "severity": "none", "explanation": "...", "suggestion": ""},
  "error_handling": {"status": 1, "severity": "medium", "explanation": "...", "suggestion": "..."},
  "best_practices": {"status": 0, "severity": "none", "explanation": "...", "suggestion": ""}
}
```

For a **directory** it is a list of `{ "file": ..., "review": {...} }` objects.

**Status convention:** `status = 1` means an issue was found for that
perspective; `status = 0` means it is clean. `severity` is an added,
human-friendly ranking (`none`/`low`/`medium`/`high`/`critical`).

The `json` format additionally wraps everything with a top-level `summary`
(files reviewed, files with issues, total issues, failures).

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success. |
| `1` | Issues found (only with `--fail-on-issues`). |
| `2` | Configuration error (e.g. missing API key). |
| `3` | Input error (bad path, nothing to review). |
| `4` | Runtime error (e.g. all files failed to review). |

## Extending the perspectives

Add a `ReviewCategory` to `DEFAULT_CATEGORIES` in
`code_review_agent/config.py`; the prompt, JSON schema, engine and formatter
all pick it up automatically.

## Development

```bash
pip install -e '.[dev]'
pytest            # runs the hermetic test suite (no API key required)
```

The test suite injects a fake OpenAI client, so it runs offline and for free.

## Architecture

```
code_review_agent/
├── cli.py         # argument parsing, orchestration, exit codes
├── config.py      # .env loading, Settings, review perspectives
├── collector.py   # file/directory discovery, language filtering
├── prompts.py     # system prompt, JSON schema, user prompt builder
├── reviewer.py    # OpenAI calls: retries, concurrency, JSON parsing
├── formatter.py   # review / json / pretty renderers
└── models.py      # dataclasses + the stable output contract
```
