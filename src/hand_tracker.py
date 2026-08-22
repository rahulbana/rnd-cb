"""MediaPipe hand-landmark detection wrapper.

MediaPipe Hands runs a TensorFlow-Lite palm-detection + landmark model to find
21 3D landmarks per hand. This module hides the MediaPipe plumbing behind a
tiny interface: feed it a BGR frame, get back the landmarks (and optionally an
annotated frame).
"""

from __future__ import annotations

from typing import Optional, Tuple

import cv2
import mediapipe as mp

import config


class HandTracker:
    def __init__(
        self,
        max_hands: int = config.MAX_HANDS,
        detection_confidence: float = config.DETECTION_CONFIDENCE,
        tracking_confidence: float = config.TRACKING_CONFIDENCE,
    ) -> None:
        self._mp_hands = mp.solutions.hands
        self._mp_draw = mp.solutions.drawing_utils
        self._mp_styles = mp.solutions.drawing_styles
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )

    def process(self, frame_bgr):
        """Detect hands in a BGR frame.

        Returns the MediaPipe results object. Its `multi_hand_landmarks` is
        `None` when no hand is found, otherwise a list of landmark sets.
        """
        # MediaPipe expects RGB; OpenCV gives us BGR.
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False       # perf: avoid a copy
        results = self._hands.process(frame_rgb)
        return results

    def first_hand(self, results):
        """Return landmarks for the first detected hand, or None."""
        if results.multi_hand_landmarks:
            return results.multi_hand_landmarks[0]
        return None

    def handedness(self, results) -> Optional[str]:
        """Return 'Left' or 'Right' for the first detected hand, if known."""
        if results.multi_handedness:
            return results.multi_handedness[0].classification[0].label
        return None

    def draw(self, frame_bgr, results):
        """Overlay the detected landmarks/connections onto the frame."""
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self._mp_draw.draw_landmarks(
                    frame_bgr,
                    hand_landmarks,
                    self._mp_hands.HAND_CONNECTIONS,
                    self._mp_styles.get_default_hand_landmarks_style(),
                    self._mp_styles.get_default_hand_connections_style(),
                )
        return frame_bgr

    def close(self) -> None:
        self._hands.close()

    def __enter__(self) -> "HandTracker":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
