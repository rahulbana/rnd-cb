"""Generate the bundled default masks as RGBA PNGs.

Each mask is drawn on the canonical 500x500 face canvas (see :mod:`facemask.masks`)
with the eyes at (190, 210) and (310, 210). Everything is drawn at 2x resolution
and down-sampled with LANCZOS so the edges stay smooth.

These are simple, original, procedurally drawn props (sunglasses, a mustache, a
clown nose, ...) so the app has something to show out of the box. Drop your own
RGBA PNGs into ``assets/masks`` — authored on the same canvas — to add more.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .masks import CANONICAL_LEFT_EYE, CANONICAL_RIGHT_EYE, CANONICAL_SIZE

SS = 2  # supersampling factor for smooth edges
LEX, LEY = CANONICAL_LEFT_EYE
REX, REY = CANONICAL_RIGHT_EYE
CX = (LEX + REX) / 2  # face centre-line x
EYE_Y = (LEY + REY) / 2


def _canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (CANONICAL_SIZE * SS, CANONICAL_SIZE * SS), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _s(*vals: float) -> tuple:
    """Scale canonical coordinates up to the supersampled canvas."""
    return tuple(v * SS for v in vals)


def _finish(img: Image.Image, path: Path) -> None:
    img.resize((CANONICAL_SIZE, CANONICAL_SIZE), Image.LANCZOS).save(path)


def _sunglasses(path: Path) -> None:
    img, d = _canvas()
    lens = (60, 46)  # half-width, half-height of each lens
    for ex, ey in ((LEX, LEY), (REX, REY)):
        d.ellipse(_s(ex - lens[0], ey - lens[1], ex + lens[0], ey + lens[1]),
                  fill=(15, 15, 20, 235), outline=(0, 0, 0, 255), width=int(6 * SS))
    # bridge over the nose and arms towards the ears
    d.rectangle(_s(CX - 22, EYE_Y - 10, CX + 22, EYE_Y + 6),
                fill=(0, 0, 0, 255))
    d.line(_s(LEX - lens[0], EYE_Y, LEX - lens[0] - 60, EYE_Y - 18),
           fill=(0, 0, 0, 255), width=int(10 * SS))
    d.line(_s(REX + lens[0], EYE_Y, REX + lens[0] + 60, EYE_Y - 18),
           fill=(0, 0, 0, 255), width=int(10 * SS))
    _finish(img, path)


def _mustache(path: Path) -> None:
    img, d = _canvas()
    my = 320  # sits below the nose
    d.pieslice(_s(CX - 90, my - 45, CX + 2, my + 55), 20, 200,
               fill=(60, 40, 25, 255))
    d.pieslice(_s(CX - 2, my - 45, CX + 90, my + 55), -20, 160,
               fill=(60, 40, 25, 255))
    _finish(img, path)


def _clown_nose(path: Path) -> None:
    img, d = _canvas()
    ny = 288
    d.ellipse(_s(CX - 42, ny - 42, CX + 42, ny + 42),
              fill=(220, 30, 30, 255), outline=(150, 15, 15, 255), width=int(3 * SS))
    d.ellipse(_s(CX - 22, ny - 26, CX - 2, ny - 6), fill=(255, 150, 150, 220))
    _finish(img, path)


def _cat(path: Path) -> None:
    img, d = _canvas()
    # ears
    d.polygon(_s(150, 120, 205, 40, 245, 135), fill=(50, 50, 50, 255))
    d.polygon(_s(350, 120, 295, 40, 255, 135), fill=(50, 50, 50, 255))
    d.polygon(_s(168, 118, 205, 68, 233, 128), fill=(240, 170, 175, 255))
    d.polygon(_s(332, 118, 295, 68, 267, 128), fill=(240, 170, 175, 255))
    # nose
    ny = 300
    d.polygon(_s(CX - 22, ny, CX + 22, ny, CX, ny + 22), fill=(240, 130, 140, 255))
    # whiskers
    for dy in (-16, 0, 16):
        d.line(_s(CX - 26, ny + dy, CX - 150, ny + dy - 20),
               fill=(255, 255, 255, 230), width=int(3 * SS))
        d.line(_s(CX + 26, ny + dy, CX + 150, ny + dy - 20),
               fill=(255, 255, 255, 230), width=int(3 * SS))
    _finish(img, path)


def _surgical_mask(path: Path) -> None:
    img, d = _canvas()
    # rounded body covering the lower face
    d.rounded_rectangle(_s(CX - 135, 270, CX + 135, 430), radius=int(40 * SS),
                        fill=(120, 190, 225, 245), outline=(70, 140, 180, 255),
                        width=int(4 * SS))
    # pleats
    for yy in (312, 350, 388):
        d.line(_s(CX - 130, yy, CX + 130, yy), fill=(90, 160, 200, 200),
               width=int(4 * SS))
    # ear loops
    d.arc(_s(CX - 210, 250, CX - 70, 400), -80, 80, fill=(230, 230, 230, 255),
          width=int(7 * SS))
    d.arc(_s(CX + 70, 250, CX + 210, 400), 100, 260, fill=(230, 230, 230, 255),
          width=int(7 * SS))
    _finish(img, path)


def _superhero(path: Path) -> None:
    img, d = _canvas()
    color = (30, 40, 120, 240)
    # a domino eye mask
    d.rounded_rectangle(_s(LEX - 95, EYE_Y - 55, REX + 95, EYE_Y + 50),
                        radius=int(50 * SS), fill=color)
    # cut out the eye holes by punching transparent ellipses
    for ex, ey in ((LEX, LEY), (REX, REY)):
        d.ellipse(_s(ex - 46, ey - 30, ex + 46, ey + 30), fill=(0, 0, 0, 0))
    # little upward flick at the outer corners
    d.polygon(_s(LEX - 95, EYE_Y - 20, LEX - 150, EYE_Y - 60, LEX - 90, EYE_Y + 10),
              fill=color)
    d.polygon(_s(REX + 95, EYE_Y - 20, REX + 150, EYE_Y - 60, REX + 90, EYE_Y + 10),
              fill=color)
    _finish(img, path)


# name -> drawing function. Numeric prefixes give a stable, friendly order.
_BUILDERS = {
    "01_sunglasses": _sunglasses,
    "02_superhero": _superhero,
    "03_mustache": _mustache,
    "04_clown_nose": _clown_nose,
    "05_cat": _cat,
    "06_surgical_mask": _surgical_mask,
}


def generate_default_masks(masks_dir: Path) -> None:
    """Draw every bundled mask into ``masks_dir`` (created if needed)."""
    masks_dir = Path(masks_dir)
    masks_dir.mkdir(parents=True, exist_ok=True)
    for name, builder in _BUILDERS.items():
        builder(masks_dir / f"{name}.png")


if __name__ == "__main__":  # allow `python -m facemask.mask_factory`
    generate_default_masks(Path(__file__).resolve().parent.parent / "assets" / "masks")
    print("Default masks written to assets/masks/")
