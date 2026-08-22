"""Small shared helpers: landmark normalisation and an FPS meter."""

from __future__ import annotations

import time
from typing import List, Sequence

import numpy as np


def landmarks_to_array(landmarks) -> np.ndarray:
    """Flatten a MediaPipe hand-landmark list into a (63,) float32 array.

    Each of the 21 landmarks contributes its (x, y, z) coordinate. MediaPipe
    already returns x and y normalised to [0, 1] relative to the image, and z
    as a relative depth.
    """
    coords = []
    for lm in landmarks.landmark:
        coords.extend((lm.x, lm.y, lm.z))
    return np.asarray(coords, dtype=np.float32)


def normalize_landmarks(flat: np.ndarray) -> np.ndarray:
    """Make landmark features translation- and scale-invariant.

    The raw coordinates depend on where the hand is in the frame and how big it
    appears. We translate so the wrist (landmark 0) sits at the origin, then
    scale by the largest absolute coordinate so the hand fits in a unit box.
    This lets the classifier focus on the *shape* of the hand, not its position
    or distance from the camera.
    """
    pts = flat.reshape(-1, 3).copy()          # (21, 3)
    wrist = pts[0].copy()
    pts -= wrist                              # translate wrist -> origin

    max_value = np.max(np.abs(pts))
    if max_value > 1e-6:
        pts /= max_value                      # scale into [-1, 1]

    return pts.reshape(-1).astype(np.float32)  # (63,)


class FPS:
    """Exponential moving-average frames-per-second counter."""

    def __init__(self, smoothing: float = 0.9) -> None:
        self._smoothing = smoothing
        self._fps = 0.0
        self._last = time.time()

    def update(self) -> float:
        now = time.time()
        dt = now - self._last
        self._last = now
        if dt > 0:
            instant = 1.0 / dt
            self._fps = self._smoothing * self._fps + (1 - self._smoothing) * instant
        return self._fps

    @property
    def value(self) -> float:
        return self._fps


def most_common(seq: Sequence[str]) -> str:
    """Return the most frequent item in a short sequence (majority vote)."""
    if not seq:
        return "none"
    counts: dict[str, int] = {}
    for item in seq:
        counts[item] = counts.get(item, 0) + 1
    return max(counts, key=counts.get)
