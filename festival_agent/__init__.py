"""festival_agent — ask an OpenAI-powered agent when a festival was celebrated.

Example:
    >>> from festival_agent import FestivalAgent
    >>> agent = FestivalAgent()
    >>> result = agent.lookup("Diwali", 1984)
    >>> print(result.date)
"""

from .agent import FestivalAgent, FestivalResult

__all__ = ["FestivalAgent", "FestivalResult"]
__version__ = "0.1.0"
