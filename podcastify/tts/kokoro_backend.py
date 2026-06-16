"""Kokoro TTS backend (default).

Kokoro is an Apache-2.0 licensed, open-weights text-to-speech model with a
range of natural-sounding English voices — ideal for giving the two podcast
hosts distinct voices, completely free and runnable locally.

    pip install kokoro soundfile

See: https://huggingface.co/hexgrad/Kokoro-82M
"""

from __future__ import annotations

import numpy as np

from .base import TTSBackend, TTSClip

# A couple of clearly distinct default voices (female / male).
_DEFAULT_HOST = "af_heart"
_DEFAULT_COHOST = "am_michael"

_VOICES = {
    "af_heart": "US English, female, warm",
    "af_bella": "US English, female, bright",
    "am_michael": "US English, male, calm",
    "am_adam": "US English, male, energetic",
    "bf_emma": "British English, female",
    "bm_george": "British English, male",
}


class KokoroBackend(TTSBackend):
    name = "kokoro"
    default_voices = (_DEFAULT_HOST, _DEFAULT_COHOST)

    def __init__(self, lang_code: str = "a") -> None:
        # Imported lazily so the package is only required when this backend
        # is actually selected.
        try:
            from kokoro import KPipeline
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Kokoro is not installed. Run `pip install kokoro soundfile` "
                "or choose a different TTS backend (e.g. --tts piper)."
            ) from exc

        self._sample_rate = 24000
        self._pipeline = KPipeline(lang_code=lang_code)

    def synthesize(self, text: str, voice: str) -> TTSClip:
        voice = voice or self.default_voices[0]
        chunks = []
        # KPipeline yields (graphemes, phonemes, audio) per sentence chunk.
        for _, _, audio in self._pipeline(text, voice=voice):
            chunks.append(np.asarray(audio, dtype=np.float32))
        if not chunks:
            samples = np.zeros(1, dtype=np.float32)
        else:
            samples = np.concatenate(chunks)
        return TTSClip(samples=samples, sample_rate=self._sample_rate)

    def available_voices(self):
        return dict(_VOICES)
