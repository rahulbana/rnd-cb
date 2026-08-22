"""
Gesture Control — control your laptop with hand gestures from the webcam.

Pipeline:
    webcam frame  ->  MediaPipe hand landmarks  ->  gesture classifier
                  ->  stability/debounce engine  ->  laptop action

The classifier is either a trained TensorFlow model (if one exists at
config.MODEL_PATH) or a built-in geometric rule-based recogniser that needs no
training.

Run:
    python main.py                 # use best available classifier
    python main.py --rules         # force the rule-based classifier
    python main.py --no-window     # headless (no preview window)

Press 'q' in the preview window (or Ctrl+C) to quit.
"""

from __future__ import annotations

import argparse
import sys

import cv2

import config
from src.hand_tracker import HandTracker
from src.rule_gestures import classify as rule_classify
from src.engine import GestureEngine
from src.controller import SystemController
from src.utils import FPS


def build_classifier(force_rules: bool):
    """Return a callable(landmarks, handedness) -> (gesture, confidence)."""
    if not force_rules and config.USE_TRAINED_MODEL_IF_AVAILABLE:
        try:
            from src.gesture_classifier import GestureClassifier

            if GestureClassifier.is_available():
                clf = GestureClassifier()
                print(f"[main] using trained TensorFlow model: {config.MODEL_PATH}")
                return lambda lms, handed: clf.predict(lms)
        except Exception as exc:
            print(f"[main] could not load TensorFlow model ({exc}); "
                  "falling back to rule-based classifier.")

    print("[main] using rule-based gesture classifier.")
    return lambda lms, handed: (rule_classify(lms, handed), 1.0)


def draw_hud(frame, gesture: str, action: str, fps: float, source_label: str):
    """Draw a small heads-up display on the frame."""
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 64), (0, 0, 0), -1)
    cv2.putText(frame, f"Gesture: {gesture}", (12, 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 120), 2)
    cv2.putText(frame, f"Action: {action}", (12, 52),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
    cv2.putText(frame, f"{fps:4.1f} FPS  [{source_label}]", (w - 260, 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    cv2.putText(frame, "press 'q' to quit", (w - 260, 52),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)


def index_tip_position(landmarks) -> tuple[float, float]:
    """Normalised (x, y) of the index-finger tip, used for mouse mode."""
    tip = landmarks.landmark[8]
    return tip.x, tip.y


def main() -> int:
    parser = argparse.ArgumentParser(description="Control your laptop with hand gestures.")
    parser.add_argument("--rules", action="store_true",
                        help="Force the rule-based classifier even if a model exists.")
    parser.add_argument("--no-window", action="store_true",
                        help="Run headless without the preview window.")
    parser.add_argument("--camera", type=int, default=config.CAMERA_INDEX,
                        help="Webcam index (default from config).")
    args = parser.parse_args()

    show_window = config.SHOW_WINDOW and not args.no_window

    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    if not cap.isOpened():
        print(f"[main] ERROR: could not open camera index {args.camera}.")
        return 1

    classifier = build_classifier(args.rules)
    source_label = "rules" if args.rules else "auto"
    engine = GestureEngine(SystemController())
    fps = FPS()

    print("[main] running — show your hand to the camera. Ctrl+C to stop.")

    try:
        with HandTracker() as tracker:
            while True:
                ok, frame = cap.read()
                if not ok:
                    print("[main] camera frame grab failed; stopping.")
                    break

                if config.FLIP_HORIZONTAL:
                    frame = cv2.flip(frame, 1)

                results = tracker.process(frame)
                hand = tracker.first_hand(results)

                gesture = "none"
                index_tip = None
                if hand is not None:
                    handed = tracker.handedness(results) or "Right"
                    gesture, _conf = classifier(hand, handed)
                    index_tip = index_tip_position(hand)
                    if config.SHOW_LANDMARKS and show_window:
                        tracker.draw(frame, results)

                engine.update(gesture, index_tip_norm=index_tip)
                current_fps = fps.update()

                if show_window:
                    action = config.GESTURE_ACTIONS.get(engine.confirmed, "none")
                    draw_hud(frame, engine.confirmed, action, current_fps, source_label)
                    cv2.imshow("Gesture Control", frame)
                    if (cv2.waitKey(1) & 0xFF) in (ord("q"), 27):  # q or Esc
                        break
    except KeyboardInterrupt:
        print("\n[main] interrupted by user.")
    finally:
        cap.release()
        if show_window:
            cv2.destroyAllWindows()

    print("[main] stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
