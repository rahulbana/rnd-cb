"""Face detection using MTCNN (a TensorFlow/Keras model).

MTCNN returns, for every detected face, a bounding box, a confidence score and
five facial landmarks (both eyes, nose tip and the two mouth corners). We expose
those as simple ``Face`` objects so the rest of the app never has to know about
TensorFlow.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

# Keep TensorFlow quiet: it logs a lot of INFO/WARNING noise on import and on
# every prediction which would otherwise flood the console during a live demo.
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")


Point = Tuple[float, float]


@dataclass
class Face:
    """A single detected face."""

    box: Tuple[int, int, int, int]  # x, y, width, height
    confidence: float
    left_eye: Point
    right_eye: Point
    nose: Point
    mouth_left: Point
    mouth_right: Point

    @property
    def eye_distance(self) -> float:
        dx = self.right_eye[0] - self.left_eye[0]
        dy = self.right_eye[1] - self.left_eye[1]
        return float(np.hypot(dx, dy))


class FaceDetector:
    """Thin wrapper around :class:`mtcnn.MTCNN`.

    The heavy TensorFlow import is deferred until the detector is actually
    created, so ``--help`` and mask listing stay fast.
    """

    def __init__(self, min_confidence: float = 0.90) -> None:
        self.min_confidence = min_confidence
        # Imported here (not at module top) to avoid paying the TensorFlow
        # start-up cost unless we really need the detector.
        from mtcnn import MTCNN  # type: ignore

        self._mtcnn = MTCNN()

    def detect(self, frame_bgr: np.ndarray, scale: float = 1.0) -> List[Face]:
        """Detect faces in a BGR (OpenCV) frame and return ``Face`` objects.

        ``scale`` (0 < scale <= 1) shrinks the frame before running MTCNN, which
        is the main cost. Detections are mapped back to full-resolution
        coordinates, so a scale of 0.5 roughly quarters the detector's workload
        with little accuracy loss for a face filling much of the frame.
        """
        import cv2

        if scale <= 0 or scale > 1:
            scale = 1.0
        if scale != 1.0:
            small = cv2.resize(frame_bgr, None, fx=scale, fy=scale,
                               interpolation=cv2.INTER_AREA)
        else:
            small = frame_bgr

        inv = 1.0 / scale
        # MTCNN expects RGB, OpenCV gives us BGR.
        rgb = small[:, :, ::-1]

        def up(pt):
            return (pt[0] * inv, pt[1] * inv)

        faces: List[Face] = []
        for det in self._mtcnn.detect_faces(rgb):
            if det.get("confidence", 0.0) < self.min_confidence:
                continue
            kp = det["keypoints"]
            x, y, w, h = det["box"]
            faces.append(
                Face(
                    box=(int(x * inv), int(y * inv), int(w * inv), int(h * inv)),
                    confidence=float(det["confidence"]),
                    left_eye=up(kp["left_eye"]),
                    right_eye=up(kp["right_eye"]),
                    nose=up(kp["nose"]),
                    mouth_left=up(kp["mouth_left"]),
                    mouth_right=up(kp["mouth_right"]),
                )
            )
        return faces
