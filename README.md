# Code Reviewer

An AI-powered, multi-agent **code reviewer CLI** built on the OpenAI API.

You point it at a directory (or file) and tell it the programming language.
It collects the matching source files and runs a set of **specialised review
agents — one per category — in parallel**, then prints a color-coded report
to the terminal.

## Review categories

Each category is handled by its own dedicated agent with a focused checklist:

1. **Correctness** (highest priority) — does the code do what it claims, edge
   cases, null handling, calculation/result correctness.
2. **Security** — SQL/command injection, path traversal, XSS, hardcoded
   secrets, unsafe deserialization, auth issues.
3. **Performance** — nested loops, unnecessary/N+1 DB calls, memory usage,
   inefficient algorithms.
4. **Readability** — naming, complexity, organization.
5. **Maintainability** — duplication, long methods, large classes, coupling,
   magic numbers.
6. **Design & Architecture** — SOLID, separation of concerns, DI, layering,
   domain boundaries.
7. **Error Handling** — error levels, swallowed exceptions, cleanup, logging.

## Install

```bash
pip install -e .
```

## Configure

Set your OpenAI key (or put it in a `.env` file — see `.env.example`):

```bash
export OPENAI_API_KEY=sk-...
```

## Usage

```bash
# Review a Python project
code-reviewer ./myproject --language python

# Pick a model
code-reviewer ./src -l typescript --model gpt-4o

# Only run specific categories
code-reviewer ./src -l python -c correctness -c security

# Also export a Markdown and/or Word report
code-reviewer ./src -l python --md review.md --docx review.docx
```

The console report is always printed. `--markdown/--md` and `--docx` are
additive — pass either, both, or neither.

You can also run it as a module: `python -m code_reviewer ...`.

### Exit codes

- `0` — review completed, no critical/high findings.
- `1` — critical or high severity findings (handy for CI gating), or no files.
- `2` — usage / configuration error (e.g. missing API key, bad language).

## How it works

```
collector  →  orchestrator  →  agents (parallel LLM calls)  →  report
   |               |                    |                         |
 gather         dispatch          one agent per             rich console
 files        file × category       category                  output
```

Each `(file, category)` pair is an independent, structured-JSON OpenAI call
dispatched through a thread pool (`--max-workers`). Large files are truncated
to stay within the token budget (`--max-file-bytes`).

## Develop

```bash
pip install -e ".[dev]"
pytest
```

Tests use a fake LLM client, so they run without network access or an API key.
