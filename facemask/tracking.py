"""Lightweight temporal smoothing for detected faces.

MTCNN is only run every few frames (to keep the video smooth), so between runs
we reuse the last result. This smoother also blends each new detection with the
previous one (an exponential moving average) so the mask glides instead of
snapping — which removes the jitter you get from sparse detections.
"""

from __future__ import annotations

from typing import List, Optional

from .detector import Face


def _blend_pt(a, b, alpha):
    return (a[0] + (b[0] - a[0]) * alpha, a[1] + (b[1] - a[1]) * alpha)


class FaceSmoother:
    """EMA smoother. ``alpha`` in (0, 1]: higher = snappier, lower = smoother."""

    def __init__(self, alpha: float = 0.5) -> None:
        self.alpha = max(0.05, min(1.0, alpha))
        self._prev: Optional[List[Face]] = None

    def update(self, faces: List[Face]) -> List[Face]:
        prev = self._prev
        # Only blend when the face count is stable; otherwise take the new set
        # as-is (someone entered/left the frame).
        if prev is not None and len(prev) == len(faces) and faces:
            a = self.alpha
            new = sorted(faces, key=lambda f: f.box[0])
            old = sorted(prev, key=lambda f: f.box[0])
            faces = [self._blend(o, n, a) for o, n in zip(old, new)]
        self._prev = faces
        return faces

    @staticmethod
    def _blend(old: Face, new: Face, a: float) -> Face:
        box = tuple(int(o + (n - o) * a) for o, n in zip(old.box, new.box))
        return Face(
            box=box,  # type: ignore[arg-type]
            confidence=new.confidence,
            left_eye=_blend_pt(old.left_eye, new.left_eye, a),
            right_eye=_blend_pt(old.right_eye, new.right_eye, a),
            nose=_blend_pt(old.nose, new.nose, a),
            mouth_left=_blend_pt(old.mouth_left, new.mouth_left, a),
            mouth_right=_blend_pt(old.mouth_right, new.mouth_right, a),
        )
