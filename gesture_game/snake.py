"""Pure Snake game state — no rendering, no camera, no heavy dependencies.

Keeping the rules here (separate from I/O in ``play.py``) makes the game logic
trivial to unit-test.
"""

from __future__ import annotations

import random
from typing import List, Optional, Tuple

# Board size in cells.
GRID_W, GRID_H = 24, 18

DIRECTIONS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}
# Directions that would reverse the snake onto itself and are therefore ignored.
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}


class SnakeGame:
    """Grid-based Snake. Advance one cell per :meth:`step`."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        cx, cy = GRID_W // 2, GRID_H // 2
        # Snake stored head-first.
        self.snake: List[Tuple[int, int]] = [(cx - i, cy) for i in range(3)]
        self.direction = "right"
        self.pending_direction = "right"
        self.paused = False
        self.game_over = False
        self.score = 0
        self.food: Optional[Tuple[int, int]] = None
        self._place_food()

    def _place_food(self) -> None:
        free = {
            (x, y) for x in range(GRID_W) for y in range(GRID_H)
        } - set(self.snake)
        self.food = random.choice(tuple(free)) if free else None

    def set_direction(self, label: str) -> None:
        """Queue a direction change, ignoring reversals and unknown labels."""
        if label in DIRECTIONS and label != OPPOSITE.get(self.direction):
            self.pending_direction = label

    def step(self) -> None:
        """Advance the snake one cell. No-op when paused or over."""
        if self.paused or self.game_over:
            return

        self.direction = self.pending_direction
        dx, dy = DIRECTIONS[self.direction]
        hx, hy = self.snake[0]
        new_head = (hx + dx, hy + dy)

        # Wall collision.
        if not (0 <= new_head[0] < GRID_W and 0 <= new_head[1] < GRID_H):
            self.game_over = True
            return
        # Self collision (the tail cell is vacated this step unless we eat).
        if new_head in self.snake[:-1]:
            self.game_over = True
            return

        self.snake.insert(0, new_head)
        if new_head == self.food:
            self.score += 1
            self._place_food()
        else:
            self.snake.pop()
