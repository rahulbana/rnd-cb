# rnd-cb

## Celebrity Radar

A **multi-agent** web researcher that finds recent news, incidents, controversies, and
**scams** involving a celebrity or public figure.

An orchestrator fans out to several **specialized search sub-agents** that run
**concurrently**, each focused on a different angle and source set, using Anthropic's
server-side web search tool. A final synthesis agent merges their cited findings into a
single Markdown briefing with a consolidated source list.

```
                          ┌──────────────────────────────┐
                          │        Orchestrator           │
                          └───────────────┬───────────────┘
            ┌─────────────┬───────────────┼───────────────┬─────────────┐
            ▼             ▼               ▼               ▼             ▼
      Recent News    Scams &        Incidents,      Social Media   (add your own)
      & Headlines   Impersonation   Legal &         & Reaction
                                    Controversy
            └─────────────┴───────────────┼───────────────┴─────────────┘
                                          ▼
                          ┌──────────────────────────────┐
                          │   Synthesis agent → report     │
                          └──────────────────────────────┘
```

Each sub-agent searches the live web independently (Anthropic runs the search loop
server-side), so they explore different sites in parallel. Findings are grounded in
citations, and unverified rumors are flagged as such.

### Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

### Usage

```bash
python -m celebrity_radar "Taylor Swift"
python -m celebrity_radar "Elon Musk" -o report.md
```

### As a library

```python
import asyncio
from celebrity_radar import research_celebrity

report = asyncio.run(research_celebrity("Keanu Reeves"))
print(report.report)        # synthesized Markdown briefing
print(report.sources)       # consolidated [(title, url), ...]
print(report.agent_findings)  # raw per-agent results
```

### Customizing the agents

The roster lives in `celebrity_radar/config.py` as a list of `SearchAgentSpec`. Add,
remove, or re-scope agents — and pin each to specific domains via `allowed_domains` /
`blocked_domains` — then pass your own list to `research_celebrity(..., agents=[...])`.

### Notes

- Defaults to the `claude-opus-4-8` model; search agents run at low effort, synthesis at
  high effort with adaptive thinking.
- Built for legitimate research, reputation monitoring, and scam awareness. Treat
  unverified claims accordingly.
