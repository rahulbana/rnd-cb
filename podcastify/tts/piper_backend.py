"""Piper TTS backend (offline option).

Piper is an MIT-licensed, fast, fully-offline neural TTS. Voices are
downloaded as .onnx model files. Point each speaker at a different voice
model to get two distinct voices.

    pip install piper-tts

Download voices from:
    https://huggingface.co/rhasspy/piper-voices

Here ``voice`` is the path to a Piper ``.onnx`` voice model.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from .base import TTSBackend, TTSClip


class PiperBackend(TTSBackend):
    name = "piper"
    # No universal defaults — the user supplies .onnx model paths per speaker.
    default_voices = ("", "")

    def __init__(self) -> None:
        try:
            from piper import PiperVoice  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Piper is not installed. Run `pip install piper-tts` or choose "
                "a different TTS backend (e.g. --tts kokoro)."
            ) from exc
        self._PiperVoice = PiperVoice
        self._cache: dict[str, object] = {}

    def _load(self, model_path: str):
        if model_path not in self._cache:
            if not Path(model_path).exists():
                raise FileNotFoundError(
                    f"Piper voice model not found: {model_path}. Download a "
                    ".onnx voice from https://huggingface.co/rhasspy/piper-voices"
                )
            self._cache[model_path] = self._PiperVoice.load(model_path)
        return self._cache[model_path]

    def synthesize(self, text: str, voice: str) -> TTSClip:
        if not voice:
            raise ValueError(
                "Piper requires a voice model path. Set Speaker.voice to a "
                ".onnx file path."
            )
        piper_voice = self._load(voice)

        # Piper writes 16-bit PCM into a wave stream; collect and convert.
        import io

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            piper_voice.synthesize(text, wav)
        buf.seek(0)
        with wave.open(buf, "rb") as wav:
            sample_rate = wav.getframerate()
            frames = wav.readframes(wav.getnframes())
        pcm = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        return TTSClip(samples=pcm, sample_rate=sample_rate)
