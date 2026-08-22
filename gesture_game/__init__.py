"""Gesture Snake: play a game with hand gestures using MediaPipe + TensorFlow.

Public API
----------
    HandTracker        - wraps MediaPipe Hands, returns normalized landmarks.
    GestureClassifier  - TensorFlow model (with a rule-based fallback) that
                         maps landmarks to one of the GESTURES.
    GESTURES           - the ordered list of gesture class labels.
    SnakeGame          - dependency-free Snake game state machine.

``HandTracker`` pulls in MediaPipe, so it is imported lazily: you can
``import gesture_game`` (and use SnakeGame / the classifier) without MediaPipe
installed, which keeps the game logic and classifier unit-testable in minimal
environments.
"""

from .classifier import GestureClassifier, GESTURES
from .snake import SnakeGame

__all__ = ["HandTracker", "GestureClassifier", "GESTURES", "SnakeGame"]
__version__ = "1.0.0"


def __getattr__(name):
    # PEP 562 lazy attribute: only import MediaPipe when HandTracker is used.
    if name == "HandTracker":
        from .hand_tracker import HandTracker

        return HandTracker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
