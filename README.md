# Code Review Agent

A production-grade, LLM-powered **code review CLI** built on the OpenAI API.
It reviews a **single file** or an **entire directory** across 14 review
perspectives and reports concrete, structured findings as JSON.

## Review perspectives

| # | Perspective | Covers (examples) |
|---|-------------|-------------------|
| 1 | `syntax` | Syntax errors, indentation, missing/circular/unused/duplicate imports, invalid decorators |
| 2 | `error_handling` | Missing try/except, oversized try blocks, swallowed/bare except, wrong hierarchy, generic `Exception`, missing finally/cleanup, bad rethrow |
| 3 | `exception_handling` | Specific vs broad exceptions, custom exceptions, exception chaining |
| 4 | `type_safety` | Missing type hints, call types inconsistent with callee signatures |
| 5 | `data_validation` | None/empty-string checks, input & schema validation, Enum usage, dataclass validation |
| 6 | `best_practices` | PEP 8/257, naming, magic numbers, comprehensions, context managers, generators, `enumerate`/`zip`, walrus, `match`-`case`, f-strings |
| 7 | `performance` | Nested loops, repeated DB/API calls, regex recompilation, large allocations, sorting cost, string concat, repeated JSON/file I/O |
| 8 | `memory` | Large lists, leaks, cache misuse, reference cycles, globals, huge dicts, copy-vs-view |
| 9 | `resource_management` | Files/DB/connections/sockets closed, context managers, thread cleanup |
| 11 | `security` | SQLi, command/path injection, unsafe pickle/yaml, hardcoded secrets, weak hashing, `random` vs `secrets`, JWT/authn/authz, CSRF/XSS/SSRF, redirects, `eval`/`exec`, `shell=True`, temp-file & permissions |
| 16 | `code_quality` | Duplicate/dead code, long methods/classes, unused vars/methods, deep nesting, cyclomatic complexity, code smells |
| 17 | `readability` | Naming, function/class length, descriptive variable names, boolean naming |
| 18 | `documentation` | Missing/empty/stale docstrings on modules/classes/methods/functions, PEP 257, Args/Returns/Raises, comments on complex logic |
| 20 | `dependency` | Unused/undeclared packages, outdated packages, known CVEs, duplicates, version conflicts, requirements hygiene |

The perspective list is data-driven (`DEFAULT_CATEGORIES` in `config.py`) — add
or remove one and the schema, prompt, engine and formatter follow automatically.

## Features

- **File or directory** review — point it at one file or a whole tree.
- **Language-aware** collection — filters directory scans by language extension.
- **14 review perspectives** — the full taxonomy above, evaluated per file.
- **Dependency-aware** — resolves the definitions of the functions/methods a
  file calls (across the project) and feeds them to the reviewer, so wrong
  argument counts/types, misused return values and unsafe callees are caught.
- **Deterministic backstops** — a non-LLM AST pass guarantees Python **syntax
  errors** and **missing docstrings** (module/class/function/method) are always
  reported, even if the model overlooks them.
- **Actionable, exact fixes** — every finding is anchored to a line and ships
  the precise `current_code` → `suggested_code` change, not just prose.
- **Structured, machine-readable output** — strict JSON schema, plus a
  human-friendly console view with `-`/`+` diffs.
- **Enterprise-ready** — concurrency, retry with exponential backoff,
  per-file fault isolation, large-file chunking, file-size guards, robust
  response parsing, CI-friendly exit codes, and support for
  OpenAI-compatible / Azure gateways.
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

## Choosing which reviewers run (`reviewers.yaml`)

Every reviewer can be switched on or off from a YAML file. It is auto-discovered
as `reviewers.yaml` in the directory you run from, or passed with `--config`.

```yaml
reviewers:
  default: true          # fallback for reviewers not listed below
  security: false        # ...turn individual ones off
  documentation: false
```

To run **only** one reviewer, flip the default off and enable just that one:

```yaml
# only-syntax.yaml
reviewers:
  default: false         # everything off...
  syntax: true           # ...except the syntax reviewer
```

```bash
code-review app.py python --config only-syntax.yaml
# -> the output contains only the "syntax" key; nothing else runs
```

A reviewer entry can also be a mapping that gives that reviewer **its own
model** — handy for running, say, the security reviewer on a stronger model
while the rest use a cheaper one:

```yaml
reviewers:
  default: true
  security:
    enabled: true
    model: gpt-4o        # security runs on gpt-4o; everything else on the default
```

Reviewers that share a model are batched into a single call; a reviewer with a
distinct model gets its own call. The file can also override the default model
and tuning options:

```yaml
model: gpt-4o-mini
options:
  concurrency: 8
  static_checks: true
```

Precedence is **CLI flags > `reviewers.yaml` > environment/`.env` > defaults**.
The repo ships a fully-annotated `reviewers.yaml` with all 14 reviewers listed.

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
| `--config PATH` | YAML file enabling/disabling reviewers (auto-discovers `reviewers.yaml`). |
| `--no-deps` | Disable resolving callee definitions (dependency context). |
| `--no-static` | Disable deterministic AST backstops (syntax, missing docstrings). |
| `--no-color` | Disable ANSI colours in `pretty` output. |
| `--fail-on-issues` | Exit `1` if any issue is found (for CI). |
| `-v, --verbose` | Verbose logging to stderr. |

You can also run it as a module: `python -m code_review_agent <path> <language>`.

## Output format

The default `review` format matches the requested contract. For a **single
file** it is the review object directly. Every flagged perspective carries an
`issues` array where each issue pins the problem to a **line** and gives the
**exact code to change** (`current_code`) and the **exact replacement/addition**
(`suggested_code`) so a fix can be applied directly:

```json
{
  "security": {
    "status": 1,
    "severity": "critical",
    "explanation": "Command injection via os.system.",
    "suggestion": "Use subprocess with an argument list.",
    "issues": [
      {
        "line": 3,
        "end_line": 3,
        "severity": "critical",
        "explanation": "os.system runs an unsanitized string.",
        "current_code": "    os.system(cmd)",
        "suggested_code": "    subprocess.run(shlex.split(cmd), check=True)"
      }
    ]
  },
  "type_safety":  {"status": 0, "severity": "none", "explanation": "...", "suggestion": "", "issues": []},
  "dependency":   {"status": 0, "severity": "none", "explanation": "...", "suggestion": "", "issues": []}
}
```

The object has **one key per perspective** (all 14 from the table above). For a
**directory** the output is a list of `{ "file": ..., "review": {...} }` objects.

**Status convention:** `status = 1` means an issue was found for that
perspective; `status = 0` means it is clean. `severity` is a human-friendly
ranking (`none`/`low`/`medium`/`high`/`critical`).

**Exact code fixes:** each `issues[]` entry contains `line`/`end_line` anchors,
`current_code` (the exact snippet to change, or `""` for a pure addition) and
`suggested_code` (the exact code to apply). The `pretty` format renders these
as a `-`/`+` diff.

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

## Cross-file context

Reviewing a file in isolation misses bugs that only show up with wider context.
Before reviewing a file the agent gathers two kinds of context and injects them
into the prompt:

**1. Callee definitions.** It builds a symbol index of function/method/class
definitions across the project, detects which symbols the file **calls**, and
supplies the matching definitions as a `DEPENDENCY DEFINITIONS` block. This lets
`type_safety` and other perspectives verify each call against the real
signature — e.g. if `caller.py` calls `charge(cid)` but `billing.py` defines
`charge(customer_id, amount)`, the missing argument is flagged with an exact
fix. The model is told **not** to speculate about symbols it wasn't shown.
Disable with `--no-deps` / `REVIEW_RESOLVE_DEPS=false`; tune via
`REVIEW_MAX_DEP_DEFS`, `REVIEW_MAX_DEP_CHARS`, `REVIEW_MAX_INDEX_FILES`.

**2. Dependency manifests.** It discovers `requirements*.txt`, `pyproject.toml`,
`setup.cfg/py`, `Pipfile` etc. near the project root and supplies them as a
`PROJECT DEPENDENCIES` block, so the `dependency` perspective can compare
declared vs imported packages and flag duplicates, unpinned versions, conflicts
and known-vulnerable packages. Tune via `REVIEW_INCLUDE_MANIFESTS` and
`REVIEW_MAX_MANIFEST_CHARS`.

## Deterministic backstops

LLM judgement is not always reliable for objective, rule-based issues — a model
may decide a trivial function "doesn't need" a docstring. For Python, the agent
therefore runs a deterministic `ast`-based pass and **merges its findings into
the model's results** so certain issues are always reported:

- `syntax` — a real `SyntaxError` (with line and message).
- `documentation` — any module, class, function or method missing a docstring,
  with the exact docstring insertion as the suggested fix.

These findings are guaranteed regardless of the model, and de-duplicated
against anything the model already reported on the same line. Disable with
`--no-static` / `REVIEW_STATIC_CHECKS=false`.

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
├── cli.py          # argument parsing, orchestration, exit codes
├── config.py       # .env + YAML loading, Settings, reviewer selection
├── collector.py    # file/directory discovery, language filtering
├── dependencies.py # symbol index + callee-definition resolution
├── static_checks.py# deterministic AST backstops (syntax, docstrings)
├── prompts.py      # system prompt, JSON schema, user prompt builder
├── engine.py       # OpenAI calls: model grouping, retries, concurrency
├── formatter.py    # review / json / pretty renderers
├── models.py       # dataclasses + the stable output contract
└── reviewers/      # one module per reviewer
    ├── base.py     # Reviewer base class
    ├── registry.py # ordered registry of all reviewers
    ├── security.py # …one file per perspective (security, syntax, …)
    └── …
```

Each reviewer is a small self-contained class (`reviewers/<name>.py`) subclassing
`Reviewer`. To add one, drop in a module and register it in `registry.py`; the
prompt, schema, engine, config and output all pick it up. A reviewer can declare
its own `default_model`, or be given one per run from `reviewers.yaml` — the
engine groups reviewers by model so same-model reviewers share a call while a
reviewer with a distinct model gets its own.
