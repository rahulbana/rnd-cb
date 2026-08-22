"""System controller: turns recognised gestures into laptop actions.

Actions are cross-platform where possible:

* Volume / media  -> OS media keys via pyautogui (works on Windows, macOS, and
                     most Linux desktop environments).
* Brightness      -> screen-brightness-control library.
* Mouse move/click-> pyautogui.

Every action is guarded so a missing optional dependency (or a headless
machine) degrades gracefully to a printed message instead of crashing.
"""

from __future__ import annotations

import time
from typing import Optional, Tuple

import config

# Optional dependencies are imported defensively: the app should still start
# (e.g. to just visualise gestures) even if system-control libs are missing.
try:
    import pyautogui
    pyautogui.FAILSAFE = False   # don't abort when cursor hits a screen corner
    _HAS_PYAUTOGUI = True
except Exception as exc:  # pragma: no cover - environment dependent
    pyautogui = None
    _HAS_PYAUTOGUI = False
    _PYAUTOGUI_ERR = exc

try:
    import screen_brightness_control as sbc
    _HAS_SBC = True
except Exception:  # pragma: no cover - environment dependent
    sbc = None
    _HAS_SBC = False


class SystemController:
    """Executes named actions. Names match values in config.GESTURE_ACTIONS."""

    def __init__(self) -> None:
        self._screen_w, self._screen_h = self._screen_size()
        self._smoothed_x: Optional[float] = None
        self._smoothed_y: Optional[float] = None
        if not _HAS_PYAUTOGUI:
            print(f"[controller] pyautogui unavailable ({_PYAUTOGUI_ERR}); "
                  "mouse/media actions will be logged only.")

    # ------------------------------------------------------------------ #
    # Public dispatch
    # ------------------------------------------------------------------ #
    def perform(self, action: str) -> None:
        """Run a one-shot action by name."""
        handler = getattr(self, f"_do_{action}", None)
        if handler is None:
            print(f"[controller] unknown action: {action}")
            return
        handler()

    def move_mouse(self, norm_x: float, norm_y: float) -> None:
        """Move the cursor. Inputs are normalised [0, 1] hand positions.

        A configurable active margin is cropped from the frame so the user can
        still reach the screen edges without moving their hand out of view, and
        exponential smoothing removes jitter.
        """
        margin = config.MOUSE_ACTIVE_MARGIN
        span = max(1e-6, 1.0 - 2 * margin)
        x = min(max((norm_x - margin) / span, 0.0), 1.0)
        y = min(max((norm_y - margin) / span, 0.0), 1.0)

        target_x = x * self._screen_w
        target_y = y * self._screen_h

        a = config.MOUSE_SMOOTHING
        if self._smoothed_x is None:
            self._smoothed_x, self._smoothed_y = target_x, target_y
        else:
            self._smoothed_x = a * self._smoothed_x + (1 - a) * target_x
            self._smoothed_y = a * self._smoothed_y + (1 - a) * target_y

        if _HAS_PYAUTOGUI:
            pyautogui.moveTo(self._smoothed_x, self._smoothed_y)

    # ------------------------------------------------------------------ #
    # Individual actions
    # ------------------------------------------------------------------ #
    def _do_none(self) -> None:
        pass

    def _do_mouse_mode(self) -> None:
        # Movement is handled continuously via move_mouse(); nothing to do on
        # the discrete trigger.
        pass

    def _do_left_click(self) -> None:
        if _HAS_PYAUTOGUI:
            pyautogui.click()
        print("[action] left click")

    def _do_volume_up(self) -> None:
        self._press("volumeup")
        print("[action] volume up")

    def _do_volume_down(self) -> None:
        self._press("volumedown")
        print("[action] volume down")

    def _do_mute(self) -> None:
        self._press("volumemute")
        print("[action] mute toggle")

    def _do_play_pause(self) -> None:
        self._press("playpause")
        print("[action] play / pause")

    def _do_next_track(self) -> None:
        self._press("nexttrack")
        print("[action] next track")

    def _do_prev_track(self) -> None:
        self._press("prevtrack")
        print("[action] previous track")

    def _do_brightness_up(self) -> None:
        self._adjust_brightness(+10)

    def _do_brightness_down(self) -> None:
        self._adjust_brightness(-10)

    # ------------------------------------------------------------------ #
    # Low-level helpers
    # ------------------------------------------------------------------ #
    def _press(self, key: str) -> None:
        if _HAS_PYAUTOGUI:
            try:
                pyautogui.press(key)
            except Exception as exc:  # pragma: no cover
                print(f"[controller] could not press {key}: {exc}")

    def _adjust_brightness(self, delta: int) -> None:
        if not _HAS_SBC:
            print(f"[action] brightness {delta:+d} (screen-brightness-control "
                  "not installed)")
            return
        try:
            current = sbc.get_brightness(display=0)
            level = current[0] if isinstance(current, (list, tuple)) else current
            new_level = int(min(100, max(0, level + delta)))
            sbc.set_brightness(new_level, display=0)
            print(f"[action] brightness -> {new_level}%")
        except Exception as exc:  # pragma: no cover
            print(f"[controller] brightness change failed: {exc}")

    @staticmethod
    def _screen_size() -> Tuple[int, int]:
        if _HAS_PYAUTOGUI:
            try:
                size = pyautogui.size()
                return int(size.width), int(size.height)
            except Exception:
                pass
        return 1920, 1080  # sensible fallback for headless/unknown displays
