"""Podcastify — convert an article/blog into a 2-person audio podcast.

A small multi-agent pipeline:

    Extractor  ->  Script Writer  ->  Editor  ->  Voice / Audio agent

The "thinking" agents are powered by an OpenAI LLM. Text-to-speech uses a
free, open-source backend (Kokoro by default, Piper as an offline option).
"""

from .models import Article, PodcastScript, DialogueLine, Speaker
from .pipeline import PodcastPipeline, PipelineConfig
from .llm import LLMProvider, get_llm_provider, register_provider

__all__ = [
    "Article",
    "PodcastScript",
    "DialogueLine",
    "Speaker",
    "PodcastPipeline",
    "PipelineConfig",
    "LLMProvider",
    "get_llm_provider",
    "register_provider",
]

__version__ = "0.1.0"
