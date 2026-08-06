"""Image resizing by ratio or explicit dimensions (offline, using Pillow)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from .base import Tool, err, ok
from ..config import config


def resize_image(path: str, ratio: float | None = None,
                 width: int | None = None, height: int | None = None,
                 output_path: str | None = None) -> dict:
    """Resize an image by a scale ratio, or to a target width/height.

    Provide either `ratio` (e.g. 0.5 to halve) OR one/both of width/height.
    If only one of width/height is given, aspect ratio is preserved.
    """
    src = Path(path).expanduser()
    if not src.exists():
        return err(f"Image not found: {src}")

    try:
        img = Image.open(src)
    except Exception as exc:
        return err(f"Could not open image: {exc}")

    orig_w, orig_h = img.size

    if ratio is not None:
        if ratio <= 0:
            return err("ratio must be greater than 0.")
        new_w = max(1, int(orig_w * ratio))
        new_h = max(1, int(orig_h * ratio))
    elif width or height:
        if width and height:
            new_w, new_h = int(width), int(height)
        elif width:
            new_w = int(width)
            new_h = max(1, int(orig_h * (new_w / orig_w)))
        else:
            new_h = int(height)
            new_w = max(1, int(orig_w * (new_h / orig_h)))
    else:
        return err("Provide either 'ratio' or 'width'/'height'.")

    resized = img.resize((new_w, new_h), Image.LANCZOS)

    if output_path:
        out = Path(output_path).expanduser()
    else:
        out = config.EXPORT_DIR / f"{src.stem}_{new_w}x{new_h}{src.suffix}"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        resized.save(out)
    except Exception as exc:
        return err(f"Could not save resized image: {exc}")

    return ok({
        "input": str(src),
        "output": str(out),
        "original_size": [orig_w, orig_h],
        "new_size": [new_w, new_h],
    })


def get_tools() -> list[Tool]:
    return [
        Tool(
            name="resize_image",
            description="Resize an image file by a scale ratio (e.g. 0.5) or to a "
                        "target width/height in pixels. Saves a new file.",
            category="Media",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the source image file."},
                    "ratio": {"type": "number", "description": "Scale factor, e.g. 0.5 to halve."},
                    "width": {"type": "integer", "description": "Target width in pixels."},
                    "height": {"type": "integer", "description": "Target height in pixels."},
                    "output_path": {"type": "string", "description": "Optional output file path."},
                },
                "required": ["path"],
            },
            func=resize_image,
        )
    ]
