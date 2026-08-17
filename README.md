# rnd-cb
RND CB

## Tic Tac Toe (Python)

A modern Tic Tac Toe game with a clean dark-themed GUI built on Python's
standard-library `tkinter`.

### Features

- **Two modes**
  - **Player vs Player** — two humans share the keyboard/mouse.
  - **Player vs Computer** — play against an AI.
- **AI difficulty** (Player vs Computer)
  - **Hard** — minimax; the computer is unbeatable (you can only draw).
  - **Easy** — mostly random, so it's winnable.
- Live scoreboard (X wins / draws / O wins) that persists across rounds.
- Modern UI: dark palette, colored marks, hover highlighting, and a
  highlighted winning line.

### Run it

```bash
python tic_tac_toe.py
```

Requires only the Python standard library. `tkinter` ships with most
CPython installs; on Debian/Ubuntu install it with:

```bash
sudo apt-get install python3-tk
```

### Files

- `tic_tac_toe.py` — the tkinter UI and game flow.
- `game.py` — pure, UI-free game logic (board rules + minimax AI), easy to
  test or reuse.
