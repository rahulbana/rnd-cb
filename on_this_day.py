#!/usr/bin/env python3
"""Convenience entry point so the agent can be run as `python on_this_day.py`.

Equivalent to `python -m history_agent.cli`, but also loads environment variables
from a local `.env` file (e.g. OPENAI_API_KEY) before running.
"""

try:
    from dotenv import load_dotenv

    load_dotenv()  # read key=value pairs from a .env file in the working dir
except ImportError:
    # python-dotenv is optional; env vars set in the shell still work.
    pass

from history_agent.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
