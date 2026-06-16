#!/usr/bin/env python3
"""Convenience entry point so the agent can be run as `python on_this_day.py`.

Equivalent to `python -m history_agent.cli`.
"""

from history_agent.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
