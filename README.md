# Tic Tac Toe 🎮

A modern Tic Tac Toe game written in Python with a clean, dark-themed GUI
built on the standard-library `tkinter` — no third-party dependencies.

Play against a friend or against an unbeatable AI.

---

## Features

- **Two game modes**
  - **Player vs Player** — two humans take turns on the same computer.
  - **Player vs Computer** — challenge the AI.
- **Selectable AI difficulty** (Player vs Computer)
  - **Hard** — powered by the [minimax](https://en.wikipedia.org/wiki/Minimax)
    algorithm; the computer plays perfectly, so the best you can do is draw.
  - **Easy** — plays mostly at random, so it's winnable.
- **Live scoreboard** tracking X wins, draws, and O wins across rounds.
- **Modern UI** — dark palette, colour-coded marks (cyan **X**, pink **O**),
  hover highlighting, a highlighted winning line, and flat custom buttons.
- **Clean architecture** — game rules and AI live in a UI-free module, so the
  logic is easy to test or reuse behind any front end.

---

## Requirements

- **Python 3.8+**
- **tkinter** — bundled with most CPython installations (Windows and macOS
  installers include it). On Debian/Ubuntu, install it separately:

  ```bash
  sudo apt-get install python3-tk
  ```

Check that tkinter is available:

```bash
python -c "import tkinter; print('tkinter', tkinter.TkVersion)"
```

---

## Getting started

Clone the repository and run the game:

```bash
git clone https://github.com/rahulbana/rnd-cb.git
cd rnd-cb
python tic_tac_toe.py
```

---

## How to play

1. Pick a mode at the top: **Player vs Computer** or **Player vs Player**.
2. In Player vs Computer, choose a **difficulty** (Easy or Hard). You play as
   **X** and move first.
3. Click any empty cell to place your mark.
4. The first player to line up three marks — in a row, column, or diagonal —
   wins, and the winning line is highlighted. If the board fills with no
   winner, it's a draw.
5. **New Round** starts a fresh game while keeping the score.
   **Reset Scores** clears the scoreboard.

The board is a 3×3 grid indexed like this internally:

```
 0 | 1 | 2
-----------
 3 | 4 | 5
-----------
 6 | 7 | 8
```

---

## Project structure

| File              | Purpose                                                        |
| ----------------- | -------------------------------------------------------------- |
| `tic_tac_toe.py`  | The tkinter GUI, theming, and game flow.                       |
| `game.py`         | Pure, UI-free game logic — board rules and the minimax AI.     |
| `README.md`       | This file.                                                     |

Because `game.py` has no UI dependencies, you can drive the rules from a
script or a test:

```python
from game import best_move, check_winner, EMPTY

board = ["X", "X", EMPTY, "O", "O", EMPTY, EMPTY, EMPTY, EMPTY]
print(best_move(board, "X"))   # 2  → completes the top row and wins
```

---

## How the AI works

On **Hard**, the computer runs **minimax**: it explores every possible
continuation of the game and picks the move that guarantees the best outcome,
preferring the quickest win and the most stubborn defence. Because Tic Tac Toe
is a solved game, perfect play by both sides always ends in a draw — so the
Hard AI can never be beaten, only tied.

On **Easy**, the computer plays a random legal move most of the time and only
occasionally chooses the optimal one, giving you room to win.

---

## License

Released for learning and demonstration purposes. Feel free to use, modify,
and share.
