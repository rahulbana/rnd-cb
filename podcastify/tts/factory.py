"""Select a TTS backend by name."""

from __future__ import annotations

from .base import TTSBackend


def get_tts_backend(name: str = "kokoro", **kwargs) -> TTSBackend:
    """Return an initialised TTS backend.

    Parameters
    ----------
    name:
        ``"kokoro"`` (default, high quality) or ``"piper"`` (fully offline).
    """
    name = name.lower()
    if name == "kokoro":
        from .kokoro_backend import KokoroBackend

        return KokoroBackend(**kwargs)
    if name == "piper":
        from .piper_backend import PiperBackend

        return PiperBackend(**kwargs)
    raise ValueError(f"Unknown TTS backend: {name!r}. Use 'kokoro' or 'piper'.")
