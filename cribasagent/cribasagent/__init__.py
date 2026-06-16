"""cribasagent — a standalone daily current-affairs agent for UPSC aspirants.

It reads the last 24 hours of Indian English-language news, distils only the
exam-relevant general-knowledge points with an OpenAI LLM, and writes a tidy
Markdown brief.
"""

from __future__ import annotations

from .agent import CribasAgent
from .config import Config
from .models import Article, Brief

__all__ = ["CribasAgent", "Config", "Article", "Brief"]
__version__ = "0.1.0"
