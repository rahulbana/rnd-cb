"""Geometry-based gesture recognition — no training required.

This classifier inspects the raw hand landmarks and decides which fingers are
extended, then maps common finger patterns to named gestures. It is the default
recogniser so the app works the moment you plug in a webcam. For custom or more
robust gestures, train the TensorFlow model (see train/) which the app will use
automatically when present.

MediaPipe landmark indices (single hand):
    0  wrist
    1-4   thumb   (4  = tip)
    5-8   index   (8  = tip)
    9-12  middle  (12 = tip)
    13-16 ring    (16 = tip)
    17-20 pinky   (20 = tip)
"""

from __future__ import annotations

import math
from typing import List

# Landmark indices for finger tips and the joint below each tip (PIP joint).
_TIPS = {"index": 8, "middle": 12, "ring": 16, "pinky": 20}
_PIPS = {"index": 6, "middle": 10, "ring": 14, "pinky": 18}
_THUMB_TIP = 4
_THUMB_IP = 3
_THUMB_MCP = 2
_INDEX_MCP = 5
_WRIST = 0


def _distance(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _fingers_up(landmarks, handedness: str) -> List[int]:
    """Return a list [thumb, index, middle, ring, pinky] of 1/0 for up/down."""
    lm = landmarks.landmark
    fingers: List[int] = []

    # Thumb: compare tip vs the IP joint on the x-axis. The direction depends
    # on which hand it is (mirrored). Frames are usually mirror-flipped, which
    # swaps the effective handedness, so we treat the reported label directly.
    if handedness == "Right":
        fingers.append(1 if lm[_THUMB_TIP].x < lm[_THUMB_IP].x else 0)
    else:
        fingers.append(1 if lm[_THUMB_TIP].x > lm[_THUMB_IP].x else 0)

    # Other four fingers: a finger is "up" when its tip is above (smaller y)
    # its PIP joint, i.e. the finger is extended upward in image space.
    for name in ("index", "middle", "ring", "pinky"):
        tip = lm[_TIPS[name]]
        pip = lm[_PIPS[name]]
        fingers.append(1 if tip.y < pip.y else 0)

    return fingers


def _hand_scale(landmarks) -> float:
    """A rough hand size used to make distance thresholds scale-invariant."""
    lm = landmarks.landmark
    return max(_distance(lm[_WRIST], lm[_INDEX_MCP]), 1e-6)


def classify(landmarks, handedness: str = "Right") -> str:
    """Map the current hand pose to one of the named gestures in config."""
    lm = landmarks.landmark

    # Pinch is detected first: thumb tip and index tip touching, regardless of
    # the other fingers. Normalise the gap by hand size so it works at any
    # distance from the camera.
    pinch_gap = _distance(lm[_THUMB_TIP], lm[_TIPS["index"]]) / _hand_scale(landmarks)
    if pinch_gap < 0.35:
        return "pinch"

    thumb, index, middle, ring, pinky = _fingers_up(landmarks, handedness)
    total = thumb + index + middle + ring + pinky

    # Thumbs up / down: only the thumb is out, and the tip is clearly above or
    # below the wrist vertically.
    if thumb == 1 and index == 0 and middle == 0 and ring == 0 and pinky == 0:
        if lm[_THUMB_TIP].y < lm[_WRIST].y:
            return "thumbs_up"
        return "thumbs_down"

    if total == 0:
        return "fist"

    if index == 1 and middle == 0 and ring == 0 and pinky == 0:
        return "point"

    if index == 1 and middle == 1 and ring == 0 and pinky == 0:
        return "peace"

    if total >= 4:
        return "open_palm"

    return "none"
