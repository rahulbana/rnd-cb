#!/usr/bin/env python3
"""Live webcam face-mask filter.

Turns on your laptop webcam, detects faces with a TensorFlow model (MTCNN) and
overlays a mask you can switch on the fly. Masks follow each face's position,
size and tilt.

Examples
--------
    python app.py                      # start the webcam with the first mask
    python app.py --mask cat           # start on a specific mask (by name)
    python app.py --list               # list the available masks and exit
    python app.py --image selfie.jpg   # run on a still image instead of the webcam

Keyboard controls (while the window is focused)
-----------------------------------------------
    n / SPACE / ->  next mask            p / <-  previous mask
    1-9             pick a mask by number  0     no mask
    m               toggle the mask on/off
    l               toggle landmark debug dots
    s               save a screenshot to ./screenshots
    q / ESC         quit
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2

from facemask.masks import load_masks
from facemask.overlay import apply_mask_to_faces

HELP_LINES = [
    "n/->/space next   p/<- prev   1-9 pick   0 none",
    "m mask on/off   l landmarks   s save   q quit",
]


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Webcam face-mask overlay using TensorFlow (MTCNN) + OpenCV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--camera", type=int, default=0,
                   help="Webcam index to open (default: 0).")
    p.add_argument("--mask", type=str, default=None,
                   help="Name of the mask to start with (see --list).")
    p.add_argument("--list", action="store_true",
                   help="List available masks and exit.")
    p.add_argument("--image", type=str, default=None,
                   help="Process a still image instead of the webcam.")
    p.add_argument("--min-confidence", type=float, default=0.90,
                   help="Minimum face-detection confidence, 0-1 (default: 0.90).")
    p.add_argument("--width", type=int, default=640,
                   help="Requested capture width (default: 640).")
    p.add_argument("--height", type=int, default=480,
                   help="Requested capture height (default: 480).")
    p.add_argument("--detect-every", type=int, default=3, metavar="N",
                   help="Run the detector only every Nth frame and track in "
                        "between (default: 3). Higher = smoother/faster, less "
                        "responsive. 1 = detect every frame.")
    p.add_argument("--detect-scale", type=float, default=0.5, metavar="S",
                   help="Downscale factor for detection, 0-1 (default: 0.5). "
                        "Smaller = faster, less accurate for small faces.")
    p.add_argument("--smooth", type=float, default=0.5, metavar="A",
                   help="Motion smoothing 0-1 (default: 0.5). Higher = snappier, "
                        "lower = smoother but more lag.")
    p.add_argument("--no-mirror", action="store_true",
                   help="Do not mirror the webcam (mirrored is more natural).")
    return p.parse_args(argv)


def _select_start_index(masks, name) -> int:
    if not name:
        return 0
    for i, m in enumerate(masks):
        if m.name == name or m.name.split("_", 1)[-1] == name:
            return i
    sys.exit(f"No mask named {name!r}. Use --list to see the options.")


def _draw_hud(frame, mask_name, mask_on, fps):
    """Draw the current mask name, FPS and the control hints."""
    h = frame.shape[0]
    label = f"Mask: {mask_name if mask_on else 'OFF'}   {fps:4.1f} FPS"
    cv2.putText(frame, label, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(frame, label, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (60, 240, 120), 2, cv2.LINE_AA)
    for i, line in enumerate(HELP_LINES):
        y = h - 16 - (len(HELP_LINES) - 1 - i) * 24
        cv2.putText(frame, line, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, line, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (235, 235, 235), 1, cv2.LINE_AA)


def _draw_landmarks(frame, faces):
    for f in faces:
        x, y, w, h = f.box
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 200, 255), 1)
        for pt in (f.left_eye, f.right_eye, f.nose, f.mouth_left, f.mouth_right):
            cv2.circle(frame, (int(pt[0]), int(pt[1])), 3, (0, 200, 255), -1)


def _save_screenshot(frame) -> Path:
    out_dir = Path("screenshots")
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"facemask_{datetime.now():%Y%m%d_%H%M%S}.png"
    cv2.imwrite(str(path), frame)
    return path


def run_image(args, masks, detector) -> int:
    frame = cv2.imread(args.image)
    if frame is None:
        sys.exit(f"Could not read image: {args.image}")
    idx = _select_start_index(masks, args.mask)
    faces = detector.detect(frame)
    print(f"Detected {len(faces)} face(s).")
    apply_mask_to_faces(frame, faces, masks[idx])
    out = Path(args.image).with_name(Path(args.image).stem + "_masked.png")
    cv2.imwrite(str(out), frame)
    print(f"Saved {out}")
    return 0


def run_webcam(args, masks, detector) -> int:
    from facemask.tracking import FaceSmoother

    idx = _select_start_index(masks, args.mask)
    mask_on = True
    show_landmarks = False
    smoother = FaceSmoother(alpha=args.smooth)
    faces = []
    frame_no = 0
    detect_every = max(1, args.detect_every)

    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    if not cap.isOpened():
        sys.exit(
            f"Could not open webcam #{args.camera}. Is it connected and not in "
            "use by another app? Try a different --camera index."
        )

    window = "Face Mask (TensorFlow) - press q to quit"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    print("Webcam started. Focus the window and press keys to change masks.")

    prev = time.time()
    fps = 0.0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Failed to read a frame from the webcam; stopping.")
                break
            if not args.no_mirror:
                frame = cv2.flip(frame, 1)

            # Only run the (expensive) detector every Nth frame; reuse and smooth
            # the last result in between so the video stays smooth.
            if frame_no % detect_every == 0:
                detected = detector.detect(frame, scale=args.detect_scale)
                faces = smoother.update(detected)
            frame_no += 1

            if mask_on:
                apply_mask_to_faces(frame, faces, masks[idx])
            if show_landmarks:
                _draw_landmarks(frame, faces)

            now = time.time()
            fps = 0.9 * fps + 0.1 * (1.0 / max(now - prev, 1e-6))
            prev = now
            _draw_hud(frame, masks[idx].name, mask_on, fps)
            cv2.imshow(window, frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):  # q or ESC
                break
            elif key in (ord("n"), ord(" "), 83):  # 83 = right arrow
                idx = (idx + 1) % len(masks)
                mask_on = True
            elif key in (ord("p"), 81):  # 81 = left arrow
                idx = (idx - 1) % len(masks)
                mask_on = True
            elif key == ord("m"):
                mask_on = not mask_on
            elif key == ord("l"):
                show_landmarks = not show_landmarks
            elif key == ord("s"):
                print(f"Saved {_save_screenshot(frame)}")
            elif key == ord("0"):
                mask_on = False
            elif ord("1") <= key <= ord("9"):
                pick = key - ord("1")
                if pick < len(masks):
                    idx, mask_on = pick, True
            # If the user closes the window with the mouse, stop.
            if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return 0


def main(argv=None) -> int:
    args = parse_args(argv)
    masks = load_masks()
    if not masks:
        sys.exit("No masks found and none could be generated.")

    if args.list:
        print("Available masks:")
        for i, m in enumerate(masks, start=1):
            key = str(i) if i <= 9 else "-"
            print(f"  [{key}] {m.name}")
        return 0

    # Import the detector lazily so --list/--help never pay the TensorFlow cost.
    from facemask.detector import FaceDetector

    print("Loading the TensorFlow face detector (first run downloads weights)...")
    detector = FaceDetector(min_confidence=args.min_confidence)

    if args.image:
        return run_image(args, masks, detector)
    return run_webcam(args, masks, detector)


if __name__ == "__main__":
    raise SystemExit(main())
