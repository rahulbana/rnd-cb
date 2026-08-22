"""Loading and describing the available masks.

Every mask is an RGBA PNG authored on a *canonical face canvas*: a square image
in which the wearer's eyes sit at two known pixel positions. To render a mask we
map those two canonical eye points onto the two eyes MTCNN detected in the live
frame (a similarity transform: translation + rotation + uniform scale). Authoring
every mask in the same frame means a single, generic overlay routine handles
sunglasses, hats, a mustache or a full face covering alike.

Default canonical layout (see :data:`CANONICAL_SIZE`, :data:`CANONICAL_LEFT_EYE`,
:data:`CANONICAL_RIGHT_EYE`). A mask can override the eye positions by shipping a
``<name>.json`` sidecar next to its PNG::

    {"left_eye": [190, 210], "right_eye": [310, 210]}

"left_eye"/"right_eye" are from the *wearer's* point of view, matching MTCNN.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np

# Canonical canvas the bundled masks are drawn on.
CANONICAL_SIZE = 500
CANONICAL_LEFT_EYE: Tuple[float, float] = (190.0, 210.0)
CANONICAL_RIGHT_EYE: Tuple[float, float] = (310.0, 210.0)

MASKS_DIR = Path(__file__).resolve().parent.parent / "assets" / "masks"


@dataclass
class Mask:
    """An overlay image plus the canonical eye anchors used to place it."""

    name: str
    rgba: np.ndarray  # H x W x 4, uint8
    left_eye: Tuple[float, float]
    right_eye: Tuple[float, float]

    @property
    def src_anchors(self) -> np.ndarray:
        """The two canonical eye points, as a 2x2 float array."""
        return np.array([self.left_eye, self.right_eye], dtype=np.float32)


def _load_sidecar(png_path: Path) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """Return (left_eye, right_eye) for a mask, honouring a JSON sidecar."""
    sidecar = png_path.with_suffix(".json")
    if sidecar.exists():
        data = json.loads(sidecar.read_text())
        return tuple(data["left_eye"]), tuple(data["right_eye"])
    return CANONICAL_LEFT_EYE, CANONICAL_RIGHT_EYE


def load_masks(masks_dir: Path = MASKS_DIR) -> List[Mask]:
    """Load every ``*.png`` mask from ``masks_dir`` (sorted by name).

    If the directory is empty or missing, the bundled masks are generated first.
    """
    masks_dir = Path(masks_dir)
    pngs = sorted(masks_dir.glob("*.png")) if masks_dir.exists() else []
    if not pngs:
        # Lazy import so generating masks (which needs Pillow) is only required
        # when the assets are actually missing.
        from .mask_factory import generate_default_masks

        generate_default_masks(masks_dir)
        pngs = sorted(masks_dir.glob("*.png"))

    import cv2  # local import keeps module import cheap

    masks: List[Mask] = []
    for png in pngs:
        img = cv2.imread(str(png), cv2.IMREAD_UNCHANGED)
        if img is None:
            continue
        if img.shape[2] == 3:  # add an opaque alpha channel if the PNG has none
            alpha = np.full(img.shape[:2] + (1,), 255, dtype=img.dtype)
            img = np.concatenate([img, alpha], axis=2)
        left_eye, right_eye = _load_sidecar(png)
        masks.append(
            Mask(name=png.stem, rgba=img, left_eye=left_eye, right_eye=right_eye)
        )
    return masks
