# Webcam Face Mask (TensorFlow)

Turn on your laptop webcam and wear a mask that follows your face in real time.
Faces are detected with **TensorFlow** (the MTCNN model, which also returns the
eye/nose/mouth landmarks), and the mask is warped onto each face so it tracks
head position, size and tilt. You can switch masks live with the keyboard.

Six masks are bundled and drawn for you on first run — sunglasses, a superhero
domino, a mustache, a clown nose, cat ears + whiskers, and a surgical mask — and
you can drop in your own.

## How it works

1. **OpenCV** grabs frames from the webcam.
2. **MTCNN** (TensorFlow/Keras) detects each face and its two eyes.
3. Each mask is authored on a *canonical face canvas* with the eyes at fixed
   points. We compute a similarity transform (scale + rotation + translation)
   that maps those canonical eyes onto your real eyes, warp the mask with that
   transform, and alpha-composite it over the frame.

```
webcam ──▶ OpenCV frame ──▶ MTCNN (TensorFlow) ──▶ eye landmarks
                                                        │
   masked frame ◀── alpha blend ◀── warp mask ◀────────┘
```

## Setup

Requires Python 3.9–3.11 and a webcam.

```bash
pip install -r requirements.txt
```

> The first run downloads the small MTCNN weights and generates the default
> masks into `assets/masks/`.

## Run

```bash
python app.py                 # start the webcam on the first mask
python app.py --mask cat      # start on a specific mask (by name)
python app.py --list          # list available masks and exit
python app.py --camera 1      # use a different webcam
python app.py --image me.jpg  # mask a still image -> me_masked.png (no webcam)
```

### Choosing / switching masks

You can pick the starting mask with `--mask <name>` and then change it any time
while the window is focused:

| Key            | Action                         |
| -------------- | ------------------------------ |
| `n` / `→` / `Space` | next mask                 |
| `p` / `←`      | previous mask                  |
| `1`–`9`        | pick a mask by number          |
| `0`            | no mask                        |
| `m`            | toggle the mask on/off         |
| `l`            | toggle landmark debug dots     |
| `s`            | save a screenshot to `screenshots/` |
| `q` / `Esc`    | quit                           |

## Add your own mask

Drop a transparent **RGBA PNG** into `assets/masks/`. Author it on the same
500×500 canvas the bundled masks use, with the wearer's eyes at **(190, 210)**
and **(310, 210)** — the mask is aligned by those two points.

If your art uses different eye positions, add a JSON sidecar next to it, e.g.
`assets/masks/pirate.png` + `assets/masks/pirate.json`:

```json
{ "left_eye": [200, 190], "right_eye": [300, 190] }
```

`left_eye` / `right_eye` are from the wearer's point of view (matching MTCNN).
Numeric name prefixes (`01_`, `02_`, …) just control the order and the `1`–`9`
shortcuts.

Regenerate the bundled masks any time with:

```bash
python -m facemask.mask_factory
```

## Project layout

```
app.py                    # CLI + webcam loop + keyboard controls
facemask/
  detector.py             # MTCNN (TensorFlow) wrapper -> Face(box, eyes, ...)
  masks.py                # load masks + canonical eye anchors
  overlay.py              # similarity transform + alpha compositing
  mask_factory.py         # draws the bundled default masks (Pillow)
assets/masks/             # the mask PNGs (generated on first run)
requirements.txt
```

## Troubleshooting

- **"Could not open webcam #0"** — another app may be using the camera, or the
  index is wrong. Try `--camera 1`, `--camera 2`, …
- **Laggy / low FPS** — MTCNN on CPU is the bottleneck. Try a smaller capture
  size, e.g. `python app.py --width 640 --height 480`.
- **Mask not appearing** — make sure your face is well lit and facing the
  camera; press `l` to see the detected landmarks. Lower the detection
  threshold with `--min-confidence 0.8` if needed.
