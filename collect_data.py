#!/usr/bin/env python3
"""Collect labeled hand-landmark samples for training the gesture model.

Show a gesture to the webcam and press the matching key to record samples for
that class. Each key-press captures a burst of frames (the hand naturally jitters
a little, which is good for training). Samples are appended to a CSV so you can
run this repeatedly to grow your dataset.

Keys
----
  u  -> up          d -> down         l -> left
  r  -> right       f -> fist
  q / ESC -> quit and save

Aim for a few hundred samples per class, captured from different distances,
angles, and (ideally) both hands. Then train with::

    python train.py
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter
from typing import List, Optional

import cv2

from gesture_game import HandTracker
from gesture_game.classifier import GESTURES
from gesture_game.hand_tracker import FEATURE_DIM

KEY_TO_LABEL = {
    ord("u"): "up",
    ord("d"): "down",
    ord("l"): "left",
    ord("r"): "right",
    ord("f"): "fist",
}
BURST = 8  # samples captured per key press


def load_counts(path: str) -> Counter:
    counts: Counter = Counter()
    if os.path.exists(path):
        with open(path, newline="") as fh:
            for row in csv.reader(fh):
                if row:
                    counts[row[0]] += 1
    return counts


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Record gesture training data.")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--out", default="data/gestures.csv",
                        help="CSV file to append samples to.")
    args = parser.parse_args(argv)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    counts = load_counts(args.out)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"Error: could not open camera {args.camera}.", file=sys.stderr)
        return 1

    new_file = not os.path.exists(args.out)
    fh = open(args.out, "a", newline="")
    writer = csv.writer(fh)
    if new_file:
        writer.writerow(["label"] + [f"f{i}" for i in range(FEATURE_DIM)])

    print("[collect] Keys: u/d/l/r=directions, f=fist, q=quit")
    latest_features = None

    with HandTracker() as tracker:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            latest_features, _ = tracker.process(frame, draw=True)

            _draw_hud(frame, counts, latest_features is not None)
            cv2.imshow("Collect Gestures", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key in KEY_TO_LABEL and latest_features is not None:
                label = KEY_TO_LABEL[key]
                for _ in range(BURST):
                    ok, frame = cap.read()
                    if not ok:
                        break
                    frame = cv2.flip(frame, 1)
                    feats, _ = tracker.process(frame, draw=False)
                    if feats is not None:
                        writer.writerow([label] + feats.tolist())
                        counts[label] += 1

    fh.close()
    cap.release()
    cv2.destroyAllWindows()
    print(f"[collect] Saved to {args.out}. Totals: {dict(counts)}")
    return 0


def _draw_hud(frame, counts: Counter, hand: bool) -> None:
    y = 26
    cv2.putText(frame, "u/d/l/r=dir  f=fist  q=quit", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (60, 220, 220), 2, cv2.LINE_AA)
    status = "HAND OK" if hand else "no hand"
    color = (80, 220, 120) if hand else (70, 70, 230)
    cv2.putText(frame, status, (10, y + 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)
    counts_str = "  ".join(f"{g}:{counts.get(g, 0)}" for g in GESTURES)
    cv2.putText(frame, counts_str, (10, frame.shape[0] - 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (240, 240, 240), 1, cv2.LINE_AA)


if __name__ == "__main__":
    raise SystemExit(main())
