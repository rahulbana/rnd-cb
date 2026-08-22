"""Gesture engine: stabilise predictions and dispatch actions.

Raw per-frame predictions are noisy, so this engine:

1. Keeps a short history and requires a gesture to be stable for
   `config.STABLE_FRAMES` frames before it is "confirmed".
2. Fires the mapped action once per confirmation, with a per-action cooldown so
   holding a gesture doesn't spam the system — except for actions listed in
   `config.REPEATABLE_ACTIONS` (like volume), which repeat while held.
3. Handles the special "mouse_mode" gesture by streaming the hand position to
   the cursor every frame instead of firing a discrete action.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Deque, Optional

import config
from src.controller import SystemController
from src.utils import most_common


class GestureEngine:
    def __init__(self, controller: Optional[SystemController] = None) -> None:
        self._controller = controller or SystemController()
        self._history: Deque[str] = deque(maxlen=config.STABLE_FRAMES)
        self._confirmed: str = "none"
        self._last_fired: dict[str, float] = {}
        self._held_frames: int = 0
        self._last_action_for_confirmed: Optional[str] = None

    @property
    def confirmed(self) -> str:
        return self._confirmed

    def update(self, gesture: str, index_tip_norm=None) -> Optional[str]:
        """Feed one frame's gesture. Returns the action fired this frame, if any.

        `index_tip_norm` is an optional (x, y) tuple in [0, 1] used to drive the
        cursor while in mouse mode.
        """
        self._history.append(gesture)
        stable = most_common(self._history)
        is_stable = len(self._history) == self._history.maxlen and \
            self._history.count(stable) >= self._history.maxlen - 1

        if is_stable and stable != self._confirmed:
            # A new gesture just became stable.
            self._confirmed = stable
            self._held_frames = 0
            self._last_action_for_confirmed = None

        action = config.GESTURE_ACTIONS.get(self._confirmed, "none")

        # Mouse mode streams position every frame; no discrete firing.
        if action == "mouse_mode":
            if index_tip_norm is not None:
                self._controller.move_mouse(*index_tip_norm)
            self._held_frames += 1
            return None

        fired: Optional[str] = None
        if action != "none":
            if action in config.REPEATABLE_ACTIONS:
                if self._held_frames % config.REPEAT_EVERY_FRAMES == 0:
                    self._controller.perform(action)
                    fired = action
            elif self._last_action_for_confirmed is None and self._may_fire(action):
                # Fire once per fresh confirmation of a non-repeatable gesture.
                self._controller.perform(action)
                self._last_action_for_confirmed = action
                self._last_fired[action] = time.time()
                fired = action

        self._held_frames += 1
        return fired

    def _may_fire(self, action: str) -> bool:
        last = self._last_fired.get(action, 0.0)
        return (time.time() - last) >= config.ACTION_COOLDOWN
