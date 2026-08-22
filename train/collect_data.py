"""
Collect hand-landmark training samples for the TensorFlow gesture classifier.

Each sample is the 63 normalised landmark coordinates plus a class label. Data
is appended to config.DATA_PATH (a CSV) so you can build the dataset over
several sessions.

Usage:
    python -m train.collect_data --gesture thumbs_up
    python -m train.collect_data --gesture peace --samples 300

While the window is open:
    * Hold the target gesture in view; samples record automatically.
    * Press SPACE to pause/resume recording.
    * Press 'q' or Esc to stop.

Collect a few hundred samples per gesture, from slightly different angles and
distances, for a robust model. Don't forget to also collect the "none" class
(a relaxed / empty hand) so the model can recognise "no gesture".
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

import cv2

import config
from src.hand_tracker import HandTracker
from src.utils import landmarks_to_array, normalize_landmarks


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect gesture landmark samples.")
    parser.add_argument("--gesture", required=True, choices=config.GESTURES,
                        help="Which gesture label these samples represent.")
    parser.add_argument("--samples", type=int, default=200,
                        help="How many samples to collect this session.")
    parser.add_argument("--camera", type=int, default=config.CAMERA_INDEX)
    args = parser.parse_args()

    label_index = config.GESTURES.index(args.gesture)
    os.makedirs(os.path.dirname(config.DATA_PATH), exist_ok=True)
    file_exists = os.path.exists(config.DATA_PATH)

    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    if not cap.isOpened():
        print(f"[collect] ERROR: could not open camera index {args.camera}.")
        return 1

    recording = True
    collected = 0

    with open(config.DATA_PATH, "a", newline="") as fh:
        writer = csv.writer(fh)
        if not file_exists:
            header = ["label"] + [f"{axis}{i}" for i in range(21) for axis in ("x", "y", "z")]
            writer.writerow(header)

        print(f"[collect] recording '{args.gesture}' (label {label_index}). "
              f"Target: {args.samples} samples. SPACE=pause, q=quit.")

        with HandTracker() as tracker:
            while collected < args.samples:
                ok, frame = cap.read()
                if not ok:
                    break
                if config.FLIP_HORIZONTAL:
                    frame = cv2.flip(frame, 1)

                results = tracker.process(frame)
                hand = tracker.first_hand(results)

                if hand is not None:
                    tracker.draw(frame, results)
                    if recording:
                        features = normalize_landmarks(landmarks_to_array(hand))
                        writer.writerow([label_index] + features.tolist())
                        collected += 1

                status = "REC" if recording else "PAUSED"
                color = (0, 0, 255) if recording else (0, 200, 255)
                cv2.putText(frame, f"{status}  {args.gesture}: {collected}/{args.samples}",
                            (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                cv2.imshow("Collect gesture data", frame)

                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if key == ord(" "):
                    recording = not recording

    cap.release()
    cv2.destroyAllWindows()
    print(f"[collect] done. Wrote {collected} samples to {config.DATA_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
