"""
Tic Tac Toe — a modern Python game with a clean tkinter UI.

Two modes:
  * Player vs Player  — two humans take turns.
  * Player vs Computer — play against an AI that uses the minimax
    algorithm (unbeatable on "Hard", beatable on "Easy").

Run it with:

    python tic_tac_toe.py

Requires only the Python standard library (tkinter ships with most
CPython installations; on Debian/Ubuntu install `python3-tk`).
"""

from __future__ import annotations

import random
import tkinter as tk
from tkinter import font as tkfont

from game import (
    DRAW,
    EMPTY,
    PLAYER_O,
    PLAYER_X,
    available_moves,
    best_move,
    check_winner,
    is_board_full,
)

# --------------------------------------------------------------------------- #
# Theme / palette
# --------------------------------------------------------------------------- #
BG = "#12131a"            # window background
CARD = "#1b1d29"          # panel background
CELL = "#232637"          # empty cell
CELL_HOVER = "#2c3049"    # cell under the cursor
LINE_WIN = "#3a3f5c"      # winning-cell background
TEXT = "#e6e8f0"          # primary text
MUTED = "#8b90a8"         # secondary text
X_COLOR = "#4dd0e1"       # cyan
O_COLOR = "#ff7597"       # pink
ACCENT = "#7c8cff"        # buttons / highlights

# Modes
MODE_PVP = "Player vs Player"
MODE_PVC = "Player vs Computer"


class TicTacToe(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Tic Tac Toe")
        self.configure(bg=BG)
        self.resizable(False, False)

        # --- Fonts ----------------------------------------------------- #
        self.f_title = tkfont.Font(family="Helvetica", size=26, weight="bold")
        self.f_mark = tkfont.Font(family="Helvetica", size=48, weight="bold")
        self.f_status = tkfont.Font(family="Helvetica", size=15, weight="bold")
        self.f_score = tkfont.Font(family="Helvetica", size=22, weight="bold")
        self.f_small = tkfont.Font(family="Helvetica", size=11)
        self.f_btn = tkfont.Font(family="Helvetica", size=12, weight="bold")

        # --- Game state ------------------------------------------------ #
        self.board = [EMPTY] * 9
        self.current = PLAYER_X
        self.mode = MODE_PVC
        self.hard = True                 # AI difficulty for PvC
        self.human = PLAYER_X            # human plays X in PvC
        self.game_over = False
        self.scores = {PLAYER_X: 0, PLAYER_O: 0, "draw": 0}
        self.cells: list[tk.Label] = []

        self._build_ui()
        self._new_game()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        outer = tk.Frame(self, bg=BG, padx=28, pady=24)
        outer.pack()

        tk.Label(
            outer, text="Tic  Tac  Toe", font=self.f_title, bg=BG, fg=TEXT
        ).pack()

        # --- Mode selector -------------------------------------------- #
        mode_bar = tk.Frame(outer, bg=BG)
        mode_bar.pack(pady=(14, 4))
        self.mode_bar = mode_bar
        self.mode_var = tk.StringVar(value=self.mode)
        for label in (MODE_PVC, MODE_PVP):
            b = tk.Radiobutton(
                mode_bar,
                text=label,
                value=label,
                variable=self.mode_var,
                command=self._on_mode_change,
                font=self.f_small,
                indicatoron=False,
                bg=CARD,
                fg=MUTED,
                selectcolor=ACCENT,
                activebackground=CARD,
                activeforeground=TEXT,
                bd=0,
                padx=14,
                pady=7,
                width=17,
                cursor="hand2",
            )
            b.pack(side="left", padx=4)

        # --- Difficulty (only relevant in PvC) ------------------------ #
        self.diff_bar = tk.Frame(outer, bg=BG)
        self.diff_bar.pack(pady=(2, 6))
        self.diff_var = tk.StringVar(value="Hard")
        tk.Label(
            self.diff_bar, text="Difficulty:", font=self.f_small, bg=BG, fg=MUTED
        ).pack(side="left", padx=(0, 6))
        for label in ("Easy", "Hard"):
            tk.Radiobutton(
                self.diff_bar,
                text=label,
                value=label,
                variable=self.diff_var,
                command=self._on_diff_change,
                font=self.f_small,
                indicatoron=False,
                bg=CARD,
                fg=MUTED,
                selectcolor=ACCENT,
                activebackground=CARD,
                activeforeground=TEXT,
                bd=0,
                padx=12,
                pady=4,
                width=6,
                cursor="hand2",
            ).pack(side="left", padx=3)

        # --- Status ---------------------------------------------------- #
        self.status = tk.Label(
            outer, text="", font=self.f_status, bg=BG, fg=TEXT, pady=8
        )
        self.status.pack(pady=(4, 8))

        # --- Board ----------------------------------------------------- #
        board_frame = tk.Frame(outer, bg=BG)
        board_frame.pack()
        grid = tk.Frame(board_frame, bg=BG)
        grid.pack()
        for i in range(9):
            r, c = divmod(i, 3)
            cell = tk.Label(
                grid,
                text="",
                font=self.f_mark,
                bg=CELL,
                fg=TEXT,
                width=3,
                height=1,
                cursor="hand2",
            )
            cell.grid(row=r, column=c, padx=6, pady=6, ipadx=4, ipady=10)
            cell.bind("<Button-1>", lambda _e, idx=i: self._on_click(idx))
            cell.bind("<Enter>", lambda _e, idx=i: self._on_hover(idx, True))
            cell.bind("<Leave>", lambda _e, idx=i: self._on_hover(idx, False))
            self.cells.append(cell)

        # --- Scoreboard ------------------------------------------------ #
        score_bar = tk.Frame(outer, bg=BG)
        score_bar.pack(pady=(18, 6), fill="x")
        self.score_labels: dict[str, tk.Label] = {}
        for key, caption, color in (
            (PLAYER_X, "Player X", X_COLOR),
            ("draw", "Draws", MUTED),
            (PLAYER_O, "Player O", O_COLOR),
        ):
            col = tk.Frame(score_bar, bg=CARD, padx=18, pady=10)
            col.pack(side="left", expand=True, fill="both", padx=4)
            val = tk.Label(col, text="0", font=self.f_score, bg=CARD, fg=color)
            val.pack()
            tk.Label(col, text=caption, font=self.f_small, bg=CARD, fg=MUTED).pack()
            self.score_labels[key] = val

        # --- Buttons --------------------------------------------------- #
        btn_bar = tk.Frame(outer, bg=BG)
        btn_bar.pack(pady=(14, 0), fill="x")
        self._make_button(btn_bar, "New Round", self._new_game, ACCENT).pack(
            side="left", expand=True, fill="x", padx=(0, 5)
        )
        self._make_button(btn_bar, "Reset Scores", self._reset_scores, CARD).pack(
            side="left", expand=True, fill="x", padx=(5, 0)
        )

    def _make_button(self, parent, text, command, bg) -> tk.Label:
        """A flat, clickable label styled as a button (no native chrome)."""
        fg = "#0d0e14" if bg == ACCENT else TEXT
        btn = tk.Label(
            parent,
            text=text,
            font=self.f_btn,
            bg=bg,
            fg=fg,
            pady=11,
            cursor="hand2",
        )
        btn.bind("<Button-1>", lambda _e: command())
        hover = self._shade(bg)
        btn.bind("<Enter>", lambda _e: btn.config(bg=hover))
        btn.bind("<Leave>", lambda _e: btn.config(bg=bg))
        return btn

    @staticmethod
    def _shade(hex_color: str) -> str:
        """Return a slightly lighter version of a hex color for hover."""
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        r, g, b = (min(255, int(v * 1.18) + 8) for v in (r, g, b))
        return f"#{r:02x}{g:02x}{b:02x}"

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #
    def _on_mode_change(self) -> None:
        self.mode = self.mode_var.get()
        # Show difficulty only for the computer mode, restoring it to its
        # natural position just below the mode selector.
        if self.mode == MODE_PVC:
            self.diff_bar.pack(pady=(2, 6), after=self.mode_bar)
        else:
            self.diff_bar.pack_forget()
        self._new_game()

    def _on_diff_change(self) -> None:
        self.hard = self.diff_var.get() == "Hard"

    def _on_hover(self, idx: int, entering: bool) -> None:
        if self.game_over or self.board[idx] != EMPTY:
            return
        if self.mode == MODE_PVC and self.current != self.human:
            return
        self.cells[idx].config(bg=CELL_HOVER if entering else CELL)

    def _on_click(self, idx: int) -> None:
        if self.game_over or self.board[idx] != EMPTY:
            return
        if self.mode == MODE_PVC and self.current != self.human:
            return
        self._place(idx, self.current)
        if self._settle():
            return
        self._swap_turn()
        # Let the computer respond.
        if self.mode == MODE_PVC and self.current != self.human:
            self.status.config(text="Computer is thinking…", fg=MUTED)
            self.after(450, self._computer_move)

    def _computer_move(self) -> None:
        if self.game_over:
            return
        ai = self.current
        if self.hard:
            idx = best_move(self.board, ai)
        else:
            # Easy: mostly random, occasionally optimal.
            idx = (
                best_move(self.board, ai)
                if random.random() < 0.35
                else random.choice(available_moves(self.board))
            )
        self._place(idx, ai)
        if self._settle():
            return
        self._swap_turn()

    # ------------------------------------------------------------------ #
    # Core game flow
    # ------------------------------------------------------------------ #
    def _place(self, idx: int, mark: str) -> None:
        self.board[idx] = mark
        color = X_COLOR if mark == PLAYER_X else O_COLOR
        self.cells[idx].config(text=mark, fg=color, bg=CELL)

    def _swap_turn(self) -> None:
        self.current = PLAYER_O if self.current == PLAYER_X else PLAYER_X
        self._update_status()

    def _settle(self) -> bool:
        """Check for a finished game; update UI/scores. Return True if over."""
        winner, line = check_winner(self.board)
        if winner:
            self.game_over = True
            self._highlight(line)
            self.scores[winner] += 1
            who = self._name(winner)
            self.status.config(text=f"{who} wins! 🎉", fg=self._color(winner))
            self._refresh_scores()
            return True
        if is_board_full(self.board):
            self.game_over = True
            self.scores["draw"] += 1
            self.status.config(text="It's a draw!", fg=TEXT)
            self._refresh_scores()
            return True
        return False

    def _highlight(self, line) -> None:
        for idx in line:
            self.cells[idx].config(bg=LINE_WIN)

    def _update_status(self) -> None:
        if self.game_over:
            return
        if self.mode == MODE_PVC and self.current != self.human:
            self.status.config(text="Computer's turn", fg=MUTED)
        else:
            self.status.config(
                text=f"{self._name(self.current)}'s turn",
                fg=self._color(self.current),
            )

    def _refresh_scores(self) -> None:
        for key, label in self.score_labels.items():
            label.config(text=str(self.scores[key]))

    def _new_game(self) -> None:
        self.board = [EMPTY] * 9
        self.current = PLAYER_X
        self.game_over = False
        for cell in self.cells:
            cell.config(text="", bg=CELL)
        self._update_status()
        # If the computer is X, it opens.
        if self.mode == MODE_PVC and self.current != self.human:
            self.status.config(text="Computer is thinking…", fg=MUTED)
            self.after(450, self._computer_move)

    def _reset_scores(self) -> None:
        self.scores = {PLAYER_X: 0, PLAYER_O: 0, "draw": 0}
        self._refresh_scores()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _name(self, mark: str) -> str:
        if self.mode == MODE_PVC:
            if mark == self.human:
                return "You"
            return "Computer"
        return f"Player {mark}"

    @staticmethod
    def _color(mark: str) -> str:
        return X_COLOR if mark == PLAYER_X else O_COLOR


def main() -> None:
    app = TicTacToe()
    # Center the window on screen.
    app.update_idletasks()
    w, h = app.winfo_width(), app.winfo_height()
    x = (app.winfo_screenwidth() - w) // 2
    y = (app.winfo_screenheight() - h) // 3
    app.geometry(f"+{x}+{y}")
    app.mainloop()


if __name__ == "__main__":
    main()
