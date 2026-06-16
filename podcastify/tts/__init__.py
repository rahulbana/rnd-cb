"""Pluggable, free/open-source text-to-speech backends."""

from .base import TTSBackend, TTSClip
from .factory import get_tts_backend

__all__ = ["TTSBackend", "TTSClip", "get_tts_backend"]
