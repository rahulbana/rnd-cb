"""Warp a mask onto a face and alpha-composite it into the frame."""

from __future__ import annotations

import cv2
import numpy as np

from .detector import Face
from .masks import Mask


def _similarity_transform(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """2x3 affine matrix mapping two ``src`` points onto two ``dst`` points.

    Uses a *similarity* transform (uniform scale + rotation + translation) so the
    mask keeps its aspect ratio while following the head's size and tilt.
    """
    (sx0, sy0), (sx1, sy1) = src
    (dx0, dy0), (dx1, dy1) = dst

    svx, svy = sx1 - sx0, sy1 - sy0
    dvx, dvy = dx1 - dx0, dy1 - dy0

    src_len_sq = svx * svx + svy * svy
    if src_len_sq < 1e-6:
        return np.array([[1, 0, 0], [0, 1, 0]], dtype=np.float32)

    # Solve for a (scale*cos) and b (scale*sin) that rotate/scale src vec to dst.
    a = (svx * dvx + svy * dvy) / src_len_sq
    b = (svx * dvy - svy * dvx) / src_len_sq

    tx = dx0 - (a * sx0 - b * sy0)
    ty = dy0 - (b * sx0 + a * sy0)
    return np.array([[a, -b, tx], [b, a, ty]], dtype=np.float32)


def apply_mask(frame_bgr: np.ndarray, face: Face, mask: Mask) -> np.ndarray:
    """Composite ``mask`` onto ``frame_bgr`` for a single ``face`` (in place)."""
    h, w = frame_bgr.shape[:2]
    dst_anchors = np.array([face.left_eye, face.right_eye], dtype=np.float32)
    matrix = _similarity_transform(mask.src_anchors, dst_anchors)

    warped = cv2.warpAffine(
        mask.rgba,
        matrix,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )

    alpha = (warped[:, :, 3:4].astype(np.float32)) / 255.0
    mask_rgb = warped[:, :, :3].astype(np.float32)
    frame = frame_bgr.astype(np.float32)
    blended = mask_rgb * alpha + frame * (1.0 - alpha)
    frame_bgr[:] = blended.astype(np.uint8)
    return frame_bgr


def apply_mask_to_faces(frame_bgr, faces, mask):
    """Apply ``mask`` to every face in ``faces``."""
    for face in faces:
        apply_mask(frame_bgr, face, mask)
    return frame_bgr
