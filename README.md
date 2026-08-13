# testgen — an LLM CLI agent for writing test cases

`testgen` is a command-line agent that reads a source **file** or an entire
**project directory** and writes idiomatic test cases for it using an LLM.
The backend is pluggable: use **OpenAI** by default, or switch to a local
**Ollama** model with a single flag — no code changes, no API key.

## Features

- 📄 **File or project** — point it at one file or a whole directory tree.
- 🔀 **Switchable backend** — `--provider openai` (default) or `--provider ollama`.
- 🧠 **Optional guidance** — pass `-d "..."` to steer what the tests focus on.
- 🌍 **Multi-language** — Python, JS/TS, Go, Java, Ruby, Rust, PHP; picks the
  idiomatic framework (pytest, Jest, `go test`, JUnit, RSpec, …) and the right
  test-file naming convention automatically.
- 🛟 **Safe by default** — never overwrites existing tests unless you ask, and
  skips test files, `node_modules`, build dirs, etc.

## Install

```bash
pip install -r requirements.txt      # requests (+ openai for the OpenAI backend)
# or install as a command:
pip install -e .                     # provides the `testgen` command
```

Set credentials. The easiest way is a `.env` file — `testgen` loads it
automatically (searching the current directory upward), so no `export` needed:

```bash
cp .env.example .env                 # then edit in your key
# .env contains:  OPENAI_API_KEY=sk-...
testgen examples/calculator.py       # picks up the key from .env
```

You can also point at a specific file with `--env-file path/to/.env`, or just
`export OPENAI_API_KEY=sk-...` the usual way. Shell variables always take
precedence over the file. Ollama needs no key — just `ollama serve` and a
pulled model.

## Usage

```bash
# Single file, OpenAI (default)
testgen examples/calculator.py

# Whole project, local Ollama model
testgen ./src --provider ollama --model llama3

# With guidance, overwriting existing tests
testgen app.py -d "focus on the auth edge cases" --overwrite

# Collect into a mirrored tests/ tree, preview without writing
testgen ./src -o ./tests --exclude "*/migrations/*" --dry-run
```

Run without installing:

```bash
python -m testgen examples/calculator.py
```

### Key options

| Option | Description |
| --- | --- |
| `path` | File or directory to generate tests for (required). |
| `-d, --description` | Natural-language guidance for the tests. |
| `--provider` | `openai` (default) or `ollama`. |
| `--model` | Model name (default `gpt-4o-mini` / `llama3`). |
| `--api-key` / `--base-url` | OpenAI key / OpenAI-compatible endpoint. |
| `--env-file` | Load env vars from a specific `.env` file. |
| `--ollama-host` | Ollama server URL (default `http://localhost:11434`). |
| `-o, --output-dir` | Write tests under a mirrored directory tree. |
| `--include` / `--exclude` | Glob filters (repeatable). |
| `--overwrite` | Replace existing test files. |
| `--dry-run` | Generate but don't write. |

## Environment variables

| Variable | Used by |
| --- | --- |
| `OPENAI_API_KEY` | OpenAI backend |
| `OPENAI_BASE_URL` | OpenAI-compatible endpoints (Azure, OpenRouter, vLLM…) |
| `OLLAMA_HOST` | Ollama backend |

## How it works

```
path ─▶ collector ─▶ language detect ─▶ prompt builder ─▶ LLM provider ─▶ writer
        (find src)   (framework/naming)   (per-file)       (openai/ollama)  (test file)
```

The whole agent talks to one small `LLMProvider` interface (`complete(system,
user) -> str`), which is what makes the backend swappable. Adding another
provider is just one new class in `testgen/llm/`.

## Project layout

```
testgen/
  cli.py            # argument parsing + run loop
  env.py            # zero-dependency .env loader
  collector.py      # find source files (respects ignores & globs)
  languages.py      # extension -> language, framework, test-file naming
  prompts.py        # system + per-file user prompts
  generator.py      # orchestration: read -> prompt -> call -> write
  llm/
    base.py         # LLMProvider interface
    openai_provider.py
    ollama_provider.py
    factory.py      # build a provider by name
tests/              # offline unit tests (no LLM needed)
examples/           # sample code to try it on
```

## Development

```bash
pip install pytest
python -m pytest -q
```

The unit tests use a `FakeProvider`, so they run fully offline.
