# DeckForge

A **modular, multi-agent CLI** that turns your documents — and live web
research — into **colorful, presentation-ready PowerPoint decks**.

Feed it a PDF, Word doc, Markdown, plain text, or pasted content. A pipeline
of specialized agents (orchestrated with **LangGraph**) researches the topic,
designs a narrative, writes the slides, art-directs the layout, and renders a
polished `.pptx` into the `ppt/` directory. **Runs entirely in the terminal —
no web UI.**

```
research ──▶ outline ──▶ content ──▶ design ──▶ render ──▶ ppt/your-deck.pptx
```

## Features

- **Multi-format ingestion** — `.pdf`, `.docx`, `.txt`, `.md`, or pasted/piped text.
- **Web-research agent** — pulls recent facts & stats via the Tavily Search API
  (auto-skips cleanly when no key is set).
- **LangGraph orchestration** — five explicit, inspectable agent stages.
- **OpenAI-powered** writing with strict JSON-schema-validated hand-offs.
- **Seven slide layouts** — title, section, bullets, two-column, quote,
  metrics, closing.
- **Five curated themes** with enterprise typography — `midnight`, `sunset`,
  `ocean`, `forest`, `mono` — plus `auto` theme selection.
- **Fully modular** — swap the LLM, search provider, themes, or layouts in
  isolation.

## Install

```bash
pip install -r requirements.txt
# or, as an editable package exposing the `deckforge` command:
pip install -e .
```

## Configure

```bash
cp .env.example .env
# then edit .env:
#   OPENAI_API_KEY=sk-...        (required)
#   TAVILY_API_KEY=tvly-...      (optional — enables web research)
```

All settings (model, temperature, theme, output dir, max searches) are
environment-driven — see `.env.example`.

## Usage

```bash
# From a document
python -m deckforge --file report.pdf --topic "Q3 results" --theme auto

# From inline text
python -m deckforge --text "Our launch plan for Project Atlas..." --topic "Launch"

# From pasted / piped text
cat notes.md | python -m deckforge --topic "Roadmap" --slides 12
```

| Option | Description |
| --- | --- |
| `-f, --file` | Source document (`.pdf`, `.docx`, `.txt`, `.md`) |
| `-x, --text` | Inline source text |
| `-t, --topic` | Topic / instruction to steer the deck |
| `--theme` | `midnight` · `sunset` · `ocean` · `forest` · `mono` · `auto` |
| `-n, --slides` | Approximate slide count (default 10) |

The finished deck is written to `ppt/<slugified-title>.pptx`.

## Architecture

```
deckforge/
├── config.py          # Env-driven settings (pydantic-settings)
├── llm.py             # OpenAI wrapper + JSON-schema structured output
├── models.py          # Typed contracts: Deck, Slide, Outline, Metric…
├── graph.py           # LangGraph pipeline wiring the agents
├── cli.py             # Terminal entrypoint (click + rich)
├── ingestion/
│   └── loaders.py     # PDF / DOCX / TXT / MD → normalized text
├── agents/
│   ├── research.py    # Web search + fact distillation (Tavily)
│   ├── outline.py     # Narrative structure
│   ├── content.py     # Slide copywriting + layout assignment
│   └── design.py      # Structural polish + theme selection
└── deck/
    ├── themes.py      # Color palettes + typography
    └── builder.py     # python-pptx renderer (one fn per layout)
```

Each agent is a small, framework-agnostic class with a `run` method, so the
pieces stay independently testable and replaceable. The LLM provider lives
behind a single module (`llm.py`) — swapping providers means reimplementing
just that file.

## Notes

- Generated `.pptx` files and `.env` are git-ignored.
- Themes use common installed fonts (Montserrat/Poppins/Segoe UI/Calibri/
  Georgia); PowerPoint substitutes gracefully if a font is missing.
- The research agent never fabricates statistics — it only surfaces numbers
  present in the source or returned by search.
