"""Interface every TTS backend implements.

A backend turns a string + a voice id into a mono PCM waveform. The pipeline
then mixes the per-line clips into a single podcast file, so backends only
need to synthesise one utterance at a time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np


@dataclass
class TTSClip:
    """A synthesised utterance as float32 PCM in the range [-1, 1]."""

    samples: np.ndarray
    sample_rate: int


class TTSBackend:
    """Base class for free/open-source TTS backends."""

    #: Friendly identifier, e.g. "kokoro" or "piper".
    name: str = "tts"

    #: Default voice ids to assign to host / co-host when the caller does not
    #: specify one. Subclasses override this.
    default_voices: tuple[str, str] = ("", "")

    def synthesize(self, text: str, voice: str) -> TTSClip:
        """Synthesise ``text`` with ``voice`` and return a :class:`TTSClip`."""
        raise NotImplementedError

    def available_voices(self) -> Dict[str, str]:
        """Map of voice id -> human description (best effort)."""
        return {}
