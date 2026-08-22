"""Unit tests for the dependency-light parts of the game.

These cover the Snake state machine and the rule-based gesture classifier, so
they run with only ``numpy`` installed (no camera, MediaPipe, or TensorFlow
needed).

    python -m pytest tests/          # or:  python -m unittest discover tests
"""

import unittest

import numpy as np

from gesture_game import GESTURES, GestureClassifier
from gesture_game.snake import DIRECTIONS, GRID_H, GRID_W, SnakeGame


def _normalize(pts):
    pts = np.asarray(pts, dtype=np.float32)
    centered = pts - pts[0]
    m = np.max(np.abs(centered))
    if m > 1e-6:
        centered = centered / m
    return centered.flatten()


def _make_hand(index_tip, curl=False):
    """Build a minimal 21-landmark hand for the rule-based classifier."""
    pts = [[0.5, 0.5] for _ in range(21)]
    pts[0] = [0.5, 0.9]        # wrist
    pts[5] = [0.5, 0.6]        # index MCP
    pts[8] = list(index_tip)   # index tip
    for tip, pip in zip([8, 12, 16, 20], [6, 10, 14, 18]):
        if curl:
            pts[tip] = [0.5, 0.72]   # tips pulled toward wrist
            pts[pip] = [0.5, 0.5]    # pips farther from wrist
    return _normalize(pts)


class TestRuleBasedClassifier(unittest.TestCase):
    def setUp(self):
        self.clf = GestureClassifier(model_path=None)

    def test_uses_rule_based_backend(self):
        self.assertEqual(self.clf.backend, "rule-based")

    def test_pointing_directions(self):
        cases = {
            "up": (0.5, 0.3),
            "down": (0.5, 0.9),
            "left": (0.1, 0.6),
            "right": (0.9, 0.6),
        }
        for expected, tip in cases.items():
            label, conf = self.clf.predict(_make_hand(tip))
            self.assertEqual(label, expected)
            self.assertGreater(conf, 0.5)

    def test_fist_detection(self):
        label, conf = self.clf.predict(_make_hand((0.5, 0.6), curl=True))
        self.assertEqual(label, "fist")
        self.assertGreater(conf, 0.5)

    def test_labels_are_known(self):
        for tip in [(0.5, 0.3), (0.9, 0.6)]:
            label, _ = self.clf.predict(_make_hand(tip))
            self.assertIn(label, GESTURES)


class TestSnakeGame(unittest.TestCase):
    def test_initial_state(self):
        g = SnakeGame()
        self.assertEqual(g.score, 0)
        self.assertFalse(g.game_over)
        self.assertEqual(g.direction, "right")
        self.assertEqual(len(g.snake), 3)

    def test_moves_in_direction(self):
        g = SnakeGame()
        head = g.snake[0]
        g.step()
        self.assertEqual(g.snake[0], (head[0] + 1, head[1]))

    def test_reversal_is_ignored(self):
        g = SnakeGame()  # moving right
        g.set_direction("left")
        self.assertEqual(g.pending_direction, "right")

    def test_turn_applies(self):
        g = SnakeGame()
        g.set_direction("up")
        g.step()
        self.assertEqual(g.direction, "up")

    def test_eating_food_grows_and_scores(self):
        g = SnakeGame()
        length = len(g.snake)
        dx, dy = DIRECTIONS[g.direction]
        hx, hy = g.snake[0]
        g.food = (hx + dx, hy + dy)  # place food directly ahead
        g.step()
        self.assertEqual(g.score, 1)
        self.assertEqual(len(g.snake), length + 1)

    def test_wall_collision_ends_game(self):
        g = SnakeGame()
        g.snake = [(0, 5), (1, 5), (2, 5)]
        g.direction = g.pending_direction = "left"
        g.step()
        self.assertTrue(g.game_over)

    def test_self_collision_ends_game(self):
        g = SnakeGame()
        # Head at (5,5); turning down runs into the body cell (5,6), which is
        # not the tail, so the game ends.
        g.snake = [(5, 5), (6, 5), (6, 6), (5, 6), (4, 6)]
        g.direction = g.pending_direction = "left"
        g.set_direction("down")
        g.step()
        self.assertTrue(g.game_over)

    def test_pause_freezes_snake(self):
        g = SnakeGame()
        g.paused = True
        before = list(g.snake)
        g.step()
        self.assertEqual(g.snake, before)

    def test_food_within_bounds(self):
        g = SnakeGame()
        for _ in range(50):
            g._place_food()
            fx, fy = g.food
            self.assertTrue(0 <= fx < GRID_W and 0 <= fy < GRID_H)
            self.assertNotIn(g.food, g.snake)


if __name__ == "__main__":
    unittest.main()
