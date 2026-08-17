"""
Pure game logic for Tic Tac Toe.

This module has no UI dependencies so it can be unit-tested on its own
and reused by any front end. The board is a flat list of 9 cells indexed
0..8 laid out as:

    0 | 1 | 2
    ---------
    3 | 4 | 5
    ---------
    6 | 7 | 8
"""

from __future__ import annotations

EMPTY = ""
PLAYER_X = "X"
PLAYER_O = "O"
DRAW = "draw"

# All eight winning lines (rows, columns, diagonals).
WIN_LINES: tuple[tuple[int, int, int], ...] = (
    (0, 1, 2), (3, 4, 5), (6, 7, 8),   # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),   # columns
    (0, 4, 8), (2, 4, 6),              # diagonals
)


def available_moves(board: list[str]) -> list[int]:
    """Indices of all empty cells."""
    return [i for i, v in enumerate(board) if v == EMPTY]


def is_board_full(board: list[str]) -> bool:
    return all(v != EMPTY for v in board)


def check_winner(board: list[str]) -> tuple[str | None, tuple[int, int, int] | None]:
    """
    Return (winner, winning_line) if there is a winner, else (None, None).
    """
    for line in WIN_LINES:
        a, b, c = line
        if board[a] != EMPTY and board[a] == board[b] == board[c]:
            return board[a], line
    return None, None


def other(mark: str) -> str:
    return PLAYER_O if mark == PLAYER_X else PLAYER_X


def _minimax(board: list[str], to_move: str, ai: str, depth: int) -> int:
    """
    Score a board from the AI's perspective.

    Wins are ranked higher when they happen sooner (and losses when they
    happen later) by folding depth into the score, which makes the AI
    play the quickest win and the most stubborn defence.
    """
    winner, _ = check_winner(board)
    if winner == ai:
        return 10 - depth
    if winner == other(ai):
        return depth - 10
    if is_board_full(board):
        return 0

    if to_move == ai:  # maximizing
        best = -1_000
        for move in available_moves(board):
            board[move] = to_move
            best = max(best, _minimax(board, other(to_move), ai, depth + 1))
            board[move] = EMPTY
        return best
    else:  # minimizing
        best = 1_000
        for move in available_moves(board):
            board[move] = to_move
            best = min(best, _minimax(board, other(to_move), ai, depth + 1))
            board[move] = EMPTY
        return best


def best_move(board: list[str], ai: str) -> int:
    """
    Return the optimal move index for ``ai`` using minimax.

    Assumes at least one empty cell exists.
    """
    best_score = -1_000
    choice = available_moves(board)[0]
    for move in available_moves(board):
        board[move] = ai
        score = _minimax(board, other(ai), ai, 1)
        board[move] = EMPTY
        if score > best_score:
            best_score = score
            choice = move
    return choice
