"""Voice / audio agent: render a :class:`PodcastScript` to an audio file.

This agent does not use the LLM. It walks the conversation, synthesises each
line with the speaker's assigned voice using a free open-source TTS backend,
and stitches the clips into a single podcast file with small natural pauses.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

import numpy as np

from ..models import PodcastScript
from ..tts import TTSBackend, TTSClip

logger = logging.getLogger("podcastify")


class VoiceAgent:
    name = "voice"

    def __init__(self, backend: TTSBackend, gap_seconds: float = 0.35) -> None:
        self.backend = backend
        self.gap_seconds = gap_seconds

    def render(self, script: PodcastScript, out_path: str | Path) -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        voices = self._resolve_voices(script)
        logger.info("[voice] voice map: %s", voices)

        clips: list[TTSClip] = []
        for i, line in enumerate(script.lines, 1):
            voice = voices[line.speaker]
            logger.info("[voice] synth line %d/%d (%s)", i, len(script.lines), line.speaker)
            clips.append(self.backend.synthesize(line.text, voice))

        sample_rate = clips[0].sample_rate if clips else 24000
        waveform = self._concat_with_gaps(clips, sample_rate)
        self._write(waveform, sample_rate, out_path)
        logger.info("[voice] wrote %s", out_path)
        return out_path

    # -- internals ----------------------------------------------------------

    def _resolve_voices(self, script: PodcastScript) -> Dict[str, str]:
        """Assign a distinct backend voice to each of the two speakers."""
        d_host, d_cohost = self.backend.default_voices
        defaults = [d_host, d_cohost]
        voices: Dict[str, str] = {}
        for idx, sp in enumerate(script.speakers):
            voices[sp.name] = sp.voice or defaults[idx % len(defaults)]
        return voices

    def _concat_with_gaps(self, clips: list[TTSClip], sample_rate: int) -> np.ndarray:
        if not clips:
            return np.zeros(1, dtype=np.float32)
        gap = np.zeros(int(self.gap_seconds * sample_rate), dtype=np.float32)
        pieces: list[np.ndarray] = []
        for clip in clips:
            pieces.append(clip.samples.astype(np.float32))
            pieces.append(gap)
        waveform = np.concatenate(pieces) if pieces else np.zeros(1, dtype=np.float32)
        # Gentle peak normalisation to keep levels consistent.
        peak = float(np.max(np.abs(waveform))) or 1.0
        return (waveform / peak * 0.95).astype(np.float32)

    def _write(self, waveform: np.ndarray, sample_rate: int, out_path: Path) -> None:
        suffix = out_path.suffix.lower()
        if suffix == ".wav":
            self._write_wav(waveform, sample_rate, out_path)
            return
        # Non-wav (e.g. mp3): write a temp wav then transcode with pydub/ffmpeg.
        tmp_wav = out_path.with_suffix(".tmp.wav")
        self._write_wav(waveform, sample_rate, tmp_wav)
        try:
            from pydub import AudioSegment

            AudioSegment.from_wav(tmp_wav).export(
                out_path, format=suffix.lstrip(".") or "mp3"
            )
        except Exception as exc:  # pragma: no cover - ffmpeg missing etc.
            raise RuntimeError(
                f"Could not export {suffix} (is ffmpeg installed?). "
                "Try an output path ending in .wav instead."
            ) from exc
        finally:
            tmp_wav.unlink(missing_ok=True)

    def _write_wav(self, waveform: np.ndarray, sample_rate: int, out_path: Path) -> None:
        try:
            import soundfile as sf

            sf.write(str(out_path), waveform, sample_rate)
            return
        except ImportError:
            pass
        # Fallback: stdlib wave with int16 PCM.
        import wave

        pcm16 = np.clip(waveform, -1.0, 1.0)
        pcm16 = (pcm16 * 32767).astype(np.int16)
        with wave.open(str(out_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(pcm16.tobytes())
