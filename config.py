"""
Central configuration for the gesture-control application.

Everything you might want to tweak lives here: camera settings, the list of
gestures the system understands, and the mapping from each gesture to a laptop
action. Editing this file does not require touching any of the logic.
"""

from __future__ import annotations

import os

# --------------------------------------------------------------------------- #
# Camera / display
# --------------------------------------------------------------------------- #
CAMERA_INDEX = 0            # Which webcam to use (0 = default built-in camera)
FRAME_WIDTH = 960
FRAME_HEIGHT = 540
FLIP_HORIZONTAL = True      # Mirror the frame so movement feels natural
SHOW_WINDOW = True          # Draw the annotated preview window
SHOW_LANDMARKS = True       # Overlay the 21 hand landmarks

# --------------------------------------------------------------------------- #
# MediaPipe hand detection
# --------------------------------------------------------------------------- #
MAX_HANDS = 1
DETECTION_CONFIDENCE = 0.7
TRACKING_CONFIDENCE = 0.6

# --------------------------------------------------------------------------- #
# Gesture classifier
# --------------------------------------------------------------------------- #
# Ordered list of gesture labels. The index of each label is its class id used
# by the TensorFlow model. Keep this in sync with the trained model.
GESTURES = [
    "none",          # no clear gesture / relaxed hand
    "open_palm",     # all five fingers extended
    "fist",          # all fingers curled
    "point",         # index finger only
    "peace",         # index + middle extended
    "thumbs_up",     # thumb extended, pointing up
    "thumbs_down",   # thumb extended, pointing down
    "pinch",         # thumb tip touching index tip
]

# Paths for the trained TensorFlow model + its collected training data.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "gesture_model.keras")
DATA_PATH = os.path.join(BASE_DIR, "data", "landmarks.csv")

# If a trained model exists it is used; otherwise the app falls back to a
# geometric rule-based classifier that needs no training data.
USE_TRAINED_MODEL_IF_AVAILABLE = True

# A gesture must be seen for this many consecutive frames before its action
# fires. This debounces jitter and prevents accidental triggers.
STABLE_FRAMES = 6

# Minimum seconds between two triggers of the same action (rate limiting).
ACTION_COOLDOWN = 0.6

# Confidence threshold below which a model prediction is treated as "none".
MIN_CONFIDENCE = 0.75

# --------------------------------------------------------------------------- #
# Gesture -> action mapping
# --------------------------------------------------------------------------- #
# Available action names are implemented in src/controller.py:
#   volume_up, volume_down, mute, play_pause, next_track, prev_track,
#   brightness_up, brightness_down, mouse_mode, left_click, none
#
# "mouse_mode" is special: while the gesture is held, the hand moves the cursor.
GESTURE_ACTIONS = {
    "open_palm":   "mouse_mode",     # Hold an open palm to move the mouse cursor
    "fist":        "play_pause",     # Make a fist to play / pause media
    "point":       "left_click",     # Point to left-click at the cursor
    "peace":       "next_track",     # Peace sign skips to the next track
    "thumbs_up":   "volume_up",      # Thumbs up raises the volume
    "thumbs_down": "volume_down",    # Thumbs down lowers the volume
    "pinch":       "mute",           # Pinch to mute / unmute
    "none":        "none",
}

# For the special "mouse_mode" gesture, how much of the frame maps to the
# screen. A smaller active region means less hand travel to cross the screen.
MOUSE_SMOOTHING = 0.35      # 0..1 exponential smoothing (higher = smoother/slower)
MOUSE_ACTIVE_MARGIN = 0.15  # Ignore a border margin so edges are reachable

# Repeat-fire actions (like volume) trigger every N frames while held instead
# of only once. Everything else fires once per stable gesture.
REPEATABLE_ACTIONS = {"volume_up", "volume_down", "brightness_up", "brightness_down"}
REPEAT_EVERY_FRAMES = 4
