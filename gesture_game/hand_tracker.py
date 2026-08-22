"""Thin wrapper around MediaPipe Hands.

Given a BGR frame (as read by OpenCV) it returns the 21 hand landmarks for the
most prominent hand, both as raw image-space points (for drawing) and as a
translation/scale-normalized feature vector (for the classifier).
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

try:
    import mediapipe as mp
except ImportError as exc:  # pragma: no cover - dependency guard
    raise ImportError(
        "mediapipe is required. Install dependencies with:\n"
        "    pip install -r requirements.txt"
    ) from exc


NUM_LANDMARKS = 21
FEATURE_DIM = NUM_LANDMARKS * 2  # (x, y) per landmark


class HandTracker:
    """Detects a single hand and exposes its landmarks.

    Parameters
    ----------
    max_num_hands:
        How many hands MediaPipe should look for. We only use the first.
    detection_confidence / tracking_confidence:
        MediaPipe thresholds; higher = fewer false detections.
    """

    def __init__(
        self,
        max_num_hands: int = 1,
        detection_confidence: float = 0.6,
        tracking_confidence: float = 0.5,
    ) -> None:
        self._mp_hands = mp.solutions.hands
        self._mp_draw = mp.solutions.drawing_utils
        self._mp_styles = mp.solutions.drawing_styles
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )

    def process(
        self, frame_bgr: np.ndarray, draw: bool = True
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Run detection on one frame.

        Returns
        -------
        (features, raw_landmarks)
            features:       shape (42,) float32 normalized feature vector, or
                            None when no hand is found.
            raw_landmarks:  shape (21, 2) int pixel coordinates for drawing, or
                            None when no hand is found.

        When ``draw`` is True the detected hand skeleton is drawn onto
        ``frame_bgr`` in place.
        """
        # MediaPipe wants RGB and an immutable buffer for a small speed-up.
        frame_rgb = frame_bgr[:, :, ::-1]
        frame_rgb.flags.writeable = False
        results = self._hands.process(frame_rgb)

        if not results.multi_hand_landmarks:
            return None, None

        hand = results.multi_hand_landmarks[0]

        if draw:
            self._mp_draw.draw_landmarks(
                frame_bgr,
                hand,
                self._mp_hands.HAND_CONNECTIONS,
                self._mp_styles.get_default_hand_landmarks_style(),
                self._mp_styles.get_default_hand_connections_style(),
            )

        h, w = frame_bgr.shape[:2]
        pts = np.array([[lm.x, lm.y] for lm in hand.landmark], dtype=np.float32)

        raw_landmarks = np.column_stack(
            [(pts[:, 0] * w).astype(int), (pts[:, 1] * h).astype(int)]
        )
        features = normalize_landmarks(pts)
        return features, raw_landmarks

    def close(self) -> None:
        self._hands.close()

    # Allow use as a context manager.
    def __enter__(self) -> "HandTracker":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def normalize_landmarks(pts: np.ndarray) -> np.ndarray:
    """Make landmarks invariant to where the hand is and how big it looks.

    Steps:
      1. Translate so the wrist (landmark 0) is at the origin.
      2. Scale by the largest absolute coordinate so values land in [-1, 1].

    ``pts`` is a (21, 2) array of MediaPipe's normalized image coordinates.
    Returns a flat (42,) float32 vector.
    """
    centered = pts - pts[0]
    max_abs = np.max(np.abs(centered))
    if max_abs > 1e-6:
        centered = centered / max_abs
    return centered.astype(np.float32).flatten()
