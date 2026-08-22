"""Gesture classifier.

Two interchangeable back-ends map a 42-dim landmark feature vector to one of the
five gesture labels:

  * A trained TensorFlow/Keras model (loaded from disk when available).
  * A rule-based fallback derived purely from hand geometry, so the game is
    playable out of the box with **no training required**.

The public surface is intentionally tiny: build a ``GestureClassifier`` and call
``predict(features)``.
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

import numpy as np

# Ordered class labels. The index of each label is its integer class id, so the
# training pipeline and the model output stay in sync with this list.
GESTURES: List[str] = ["up", "down", "left", "right", "fist"]

# MediaPipe landmark indices we care about.
_WRIST = 0
_FINGER_TIPS = [8, 12, 16, 20]   # index, middle, ring, pinky tips
_FINGER_PIPS = [6, 10, 14, 18]   # corresponding PIP joints
_INDEX_MCP = 5
_INDEX_TIP = 8


class GestureClassifier:
    """Classify a hand pose into one of :data:`GESTURES`.

    Parameters
    ----------
    model_path:
        Path to a saved Keras model (``.keras`` or ``.h5``). If the file does
        not exist, or TensorFlow is unavailable, the classifier silently falls
        back to the geometric rule-based method.
    """

    def __init__(self, model_path: Optional[str] = "models/gesture_model.keras") -> None:
        self._model = None
        self.backend = "rule-based"
        if model_path and os.path.exists(model_path):
            self._try_load_model(model_path)

    def _try_load_model(self, model_path: str) -> None:
        try:
            import tensorflow as tf  # imported lazily; heavy dependency

            self._model = tf.keras.models.load_model(model_path)
            self.backend = "tensorflow"
        except Exception as exc:  # pragma: no cover - environment dependent
            print(f"[classifier] Could not load model '{model_path}': {exc}")
            print("[classifier] Falling back to rule-based gestures.")
            self._model = None
            self.backend = "rule-based"

    def predict(self, features: np.ndarray) -> Tuple[str, float]:
        """Return ``(label, confidence)`` for a 42-dim feature vector."""
        if self._model is not None:
            probs = self._model.predict(features[None, :], verbose=0)[0]
            idx = int(np.argmax(probs))
            return GESTURES[idx], float(probs[idx])
        return self._rule_based(features)

    # ------------------------------------------------------------------
    # Rule-based fallback
    # ------------------------------------------------------------------
    @staticmethod
    def _rule_based(features: np.ndarray) -> Tuple[str, float]:
        """Infer a gesture from raw hand geometry.

        ``features`` is the normalized (42,) vector produced by
        :func:`gesture_game.hand_tracker.normalize_landmarks`, i.e. wrist at the
        origin. We reshape back to (21, 2) points.

        A "fist" is detected when the four fingers are curled (their tips are
        closer to the wrist than their PIP joints). Otherwise the pointing
        direction is taken from the index finger and snapped to the nearest of
        up / down / left / right.
        """
        pts = features.reshape(-1, 2)

        # Curl test: for an extended finger the tip is farther from the wrist
        # than the PIP joint. For a curled finger it is closer.
        wrist = pts[_WRIST]
        curled = 0
        for tip, pip in zip(_FINGER_TIPS, _FINGER_PIPS):
            d_tip = np.linalg.norm(pts[tip] - wrist)
            d_pip = np.linalg.norm(pts[pip] - wrist)
            if d_tip < d_pip:
                curled += 1

        if curled >= 3:
            # Confidence scales with how many fingers are clearly curled.
            return "fist", 0.5 + 0.125 * curled

        # Pointing direction from the index finger base -> tip.
        base = pts[_INDEX_MCP]
        tip = pts[_INDEX_TIP]
        dx = tip[0] - base[0]
        # Image y grows downward, so negate to make "up" positive.
        dy = -(tip[1] - base[1])

        if abs(dx) >= abs(dy):
            label = "right" if dx > 0 else "left"
            confidence = abs(dx) / (abs(dx) + abs(dy) + 1e-6)
        else:
            label = "up" if dy > 0 else "down"
            confidence = abs(dy) / (abs(dx) + abs(dy) + 1e-6)

        return label, float(confidence)
