"""On This Day — a CLI agent that researches historical events for a given date.

The package exposes a small, composable API:

- :func:`history_agent.dateparse.parse_date_input` turns free-form date text into
  a structured :class:`history_agent.dateparse.ParsedDate`.
- :func:`history_agent.agent.research_date` uses an OpenAI model with web search
  to find what happened on that date and returns a Markdown report.
"""

__version__ = "0.1.0"
