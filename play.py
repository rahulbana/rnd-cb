#!/usr/bin/env python3
"""Gesture Snake — play Snake with your hand.

Point your index finger up / down / left / right to steer the snake, and make a
fist to pause. Eat the red food to grow and score; don't hit the walls or
yourself.

Controls
--------
  Hand gestures : steer (up/down/left/right), fist = pause
  r             : restart after game over
  q or ESC      : quit

Run with::

    python play.py                 # use the webcam
    python play.py --camera 1      # pick a different camera index
    python play.py --no-model      # ignore any trained model, use rules only

A trained TensorFlow model at ``models/gesture_model.keras`` is used
automatically when present; otherwise a rule-based classifier keeps the game
fully playable.
"""

from __future__ import annotations

import argparse
import collections
import sys
import time
from typing import Deque, List, Optional

import cv2
import numpy as np

from gesture_game import GestureClassifier, HandTracker
from gesture_game.snake import DIRECTIONS, GRID_H, GRID_W, SnakeGame

# ----------------------------------------------------------------------------
# Layout / tuning constants
# ----------------------------------------------------------------------------
CELL = 28                        # pixel size of one cell
HUD_H = 56                       # top status-bar height in pixels
BOARD_W = GRID_W * CELL
BOARD_H = GRID_H * CELL

CAM_PIP_W = 240                  # webcam picture-in-picture width

MOVE_INTERVAL = 0.16            # seconds between snake steps (game speed)
SMOOTH_FRAMES = 5               # gesture votes kept for smoothing

# Colors (BGR).
C_BG = (24, 24, 28)
C_GRID = (40, 40, 46)
C_SNAKE_HEAD = (80, 220, 120)
C_SNAKE_BODY = (60, 170, 95)
C_FOOD = (70, 70, 230)
C_TEXT = (240, 240, 240)
C_ACCENT = (200, 180, 60)
C_DANGER = (70, 70, 230)

class GestureSmoother:
    """Majority vote over the last few predictions to tame jitter."""

    def __init__(self, window: int = SMOOTH_FRAMES) -> None:
        self._votes: Deque[str] = collections.deque(maxlen=window)

    def update(self, label: Optional[str]) -> Optional[str]:
        if label is not None:
            self._votes.append(label)
        if not self._votes:
            return None
        return collections.Counter(self._votes).most_common(1)[0][0]

    def clear(self) -> None:
        self._votes.clear()


# ----------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------
def draw_board(game: SnakeGame) -> np.ndarray:
    canvas = np.full((BOARD_H + HUD_H, BOARD_W, 3), C_BG, dtype=np.uint8)

    # Grid lines.
    for x in range(0, BOARD_W + 1, CELL):
        cv2.line(canvas, (x, HUD_H), (x, HUD_H + BOARD_H), C_GRID, 1)
    for y in range(HUD_H, HUD_H + BOARD_H + 1, CELL):
        cv2.line(canvas, (0, y), (BOARD_W, y), C_GRID, 1)

    # Food.
    if game.food is not None:
        _fill_cell(canvas, game.food, C_FOOD, inset=5, radius=True)

    # Snake.
    for i, cell in enumerate(game.snake):
        color = C_SNAKE_HEAD if i == 0 else C_SNAKE_BODY
        _fill_cell(canvas, cell, color, inset=2)

    # HUD.
    cv2.putText(canvas, f"Score: {game.score}", (14, 36),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, C_ACCENT, 2, cv2.LINE_AA)
    hint = "Fist = pause  |  r = restart  |  q = quit"
    cv2.putText(canvas, hint, (BOARD_W - 430, 36),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, C_TEXT, 1, cv2.LINE_AA)

    if game.paused and not game.game_over:
        _center_banner(canvas, "PAUSED", C_ACCENT)
    if game.game_over:
        _center_banner(canvas, f"GAME OVER  -  Score {game.score}",
                       C_DANGER, subtitle="Press 'r' to play again")
    return canvas


def _fill_cell(canvas, cell, color, inset=2, radius=False) -> None:
    x, y = cell
    x0 = x * CELL + inset
    y0 = HUD_H + y * CELL + inset
    x1 = (x + 1) * CELL - inset
    y1 = HUD_H + (y + 1) * CELL - inset
    if radius:
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        cv2.circle(canvas, (cx, cy), (x1 - x0) // 2, color, -1, cv2.LINE_AA)
    else:
        cv2.rectangle(canvas, (x0, y0), (x1, y1), color, -1)


def _center_banner(canvas, text, color, subtitle: Optional[str] = None) -> None:
    h, w = canvas.shape[:2]
    overlay = canvas.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.45, canvas, 0.55, 0, canvas)

    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
    cv2.putText(canvas, text, ((w - tw) // 2, h // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3, cv2.LINE_AA)
    if subtitle:
        (sw, _), _ = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.putText(canvas, subtitle, ((w - sw) // 2, h // 2 + 44),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, C_TEXT, 2, cv2.LINE_AA)


def compose_camera_pip(frame, label: Optional[str], conf: float,
                       backend: str) -> np.ndarray:
    """Scale the webcam frame to a PIP panel with the current gesture readout."""
    h, w = frame.shape[:2]
    scale = CAM_PIP_W / w
    pip = cv2.resize(frame, (CAM_PIP_W, int(h * scale)))

    text = f"{label} ({conf:.0%})" if label else "no hand"
    cv2.rectangle(pip, (0, 0), (CAM_PIP_W, 26), (0, 0, 0), -1)
    cv2.putText(pip, text, (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                C_SNAKE_HEAD if label else C_DANGER, 1, cv2.LINE_AA)
    cv2.putText(pip, f"[{backend}]", (CAM_PIP_W - 96, 19),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, C_ACCENT, 1, cv2.LINE_AA)
    return pip


def stack_views(board: np.ndarray, pip: np.ndarray) -> np.ndarray:
    """Place the camera PIP into the bottom-right corner of the board."""
    out = board.copy()
    ph, pw = pip.shape[:2]
    y0 = out.shape[0] - ph - 10
    x0 = out.shape[1] - pw - 10
    cv2.rectangle(out, (x0 - 2, y0 - 2), (x0 + pw + 2, y0 + ph + 2),
                  C_ACCENT, 2)
    out[y0:y0 + ph, x0:x0 + pw] = pip
    return out


# ----------------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Play Snake with hand gestures.")
    parser.add_argument("--camera", type=int, default=0,
                        help="Webcam index (default: 0).")
    parser.add_argument("--model", default="models/gesture_model.keras",
                        help="Path to a trained Keras gesture model.")
    parser.add_argument("--no-model", action="store_true",
                        help="Ignore any trained model; use rule-based gestures.")
    args = parser.parse_args(argv)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"Error: could not open camera {args.camera}.", file=sys.stderr)
        return 1

    classifier = GestureClassifier(None if args.no_model else args.model)
    smoother = GestureSmoother()
    game = SnakeGame()

    window = "Gesture Snake"
    cv2.namedWindow(window, cv2.WINDOW_AUTOSIZE)
    print(f"[play] Gesture backend: {classifier.backend}")
    print("[play] Point to steer, fist to pause, 'r' restart, 'q' quit.")

    last_move = time.time()

    with HandTracker() as tracker:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Error: failed to read from camera.", file=sys.stderr)
                break
            frame = cv2.flip(frame, 1)  # mirror for natural interaction

            features, _ = tracker.process(frame, draw=True)
            label: Optional[str] = None
            conf = 0.0
            if features is not None:
                label, conf = classifier.predict(features)

            smoothed = smoother.update(label)

            # Apply gesture to game state.
            if smoothed == "fist":
                game.paused = True
            elif smoothed in DIRECTIONS:
                game.paused = False
                game.set_direction(smoothed)

            # Advance on a fixed timer, independent of camera FPS.
            now = time.time()
            if now - last_move >= MOVE_INTERVAL:
                game.step()
                last_move = now

            board = draw_board(game)
            pip = compose_camera_pip(frame, label, conf, classifier.backend)
            cv2.imshow(window, stack_views(board, pip))

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):  # q or ESC
                break
            if key == ord("r"):
                game.reset()
                smoother.clear()
                last_move = time.time()

            # Stop if the window was closed with the title-bar X.
            if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                break

    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
