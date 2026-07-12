"""Tool registry.

`build_tools` assembles every tool bound to the agent from the focused modules
in this package. Add a new capability by writing a ``make_*_tools`` factory and
appending it here.
"""

from __future__ import annotations

from ..config import Settings
from ..storage import LongTermMemory
from .converters import make_converter_tools
from .datetime_tools import make_time_tools
from .memory import make_memory_tools
from .network import make_network_tools
from .text import make_text_tools
from .web import make_web_tools


def build_tools(settings: Settings, chat_llm, memory: LongTermMemory) -> list:
    """Return the full list of tools bound to the agent.

    `chat_llm` is the tool-free base model, reused by the text tools for their
    internal sub-tasks.
    """
    return [
        *make_memory_tools(memory),
        *make_web_tools(settings),
        *make_converter_tools(),
        *make_time_tools(),
        *make_network_tools(),
        *make_text_tools(chat_llm),
    ]


__all__ = ["build_tools"]
