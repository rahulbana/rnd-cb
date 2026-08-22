# Gesture Snake 🐍✋

Play the classic **Snake** game with **hand gestures** — no keyboard needed.
Point your finger up / down / left / right to steer, and make a fist to pause.

Built with **Python**, **OpenCV**, **MediaPipe** (hand landmark detection) and
**TensorFlow/Keras** (gesture classification).

> It works **out of the box** with a built-in rule-based gesture recognizer.
> Want higher accuracy tuned to your own hand? Collect a few samples and train
> the included TensorFlow model — `play.py` picks it up automatically.

---

## How it works

```
 Webcam ──▶ MediaPipe Hands ──▶ 21 landmarks ──▶ normalize ──▶ Gesture
   frame     (hand_tracker.py)    (x, y) × 21      (42-d vec)   classifier
                                                                    │
                                          ┌─────────────────────────┴───────────┐
                                          ▼                                       ▼
                              TensorFlow model (if trained)          Rule-based fallback
                              (classifier.py / train.py)             (hand geometry)
                                          │                                       │
                                          └──────────────▶ up/down/left/right/fist┘
                                                                    │
                                                                    ▼
                                                        Snake game (snake.py)
                                                        rendered with OpenCV (play.py)
```

1. **MediaPipe** finds 21 hand keypoints in each webcam frame.
2. Keypoints are **translated & scaled** so recognition doesn't depend on where
   your hand is or how big it looks.
3. A **classifier** turns those keypoints into one of five gestures:
   `up`, `down`, `left`, `right`, `fist`.
4. Predictions are **smoothed** over several frames, then drive the snake.

---

## Setup

Requires **Python 3.9–3.11** and a **webcam**.

```bash
pip install -r requirements.txt
```

---

## Play

```bash
python play.py
```

| Input                     | Action                    |
|---------------------------|---------------------------|
| ☝️ point up/down/left/right | steer the snake           |
| ✊ fist                    | pause                     |
| `r`                       | restart after game over   |
| `q` or `Esc`              | quit                      |

Your webcam feed (with the detected hand skeleton and the current gesture) shows
in the bottom-right corner. Eat the red dots to grow and score; don't hit the
walls or yourself.

Options:

```bash
python play.py --camera 1     # choose a different webcam
python play.py --no-model     # force the rule-based recognizer
```

---

## (Optional) Train your own TensorFlow model

The rule-based recognizer is good, but a trained model adapts to *your* hand and
gesture style.

**1. Collect samples** — show each gesture and press its key to record a burst:

```bash
python collect_data.py
```

Keys: `u` up · `d` down · `l` left · `r` right · `f` fist · `q` quit.
Aim for a few hundred samples per gesture from varied distances and angles.
Data is appended to `data/gestures.csv` (run it as many times as you like).

**2. Train** the classifier:

```bash
python train.py
```

This trains a small Keras network and saves it to
`models/gesture_model.keras`.

**3. Play** — the model is loaded automatically. The picture-in-picture panel
shows `[tensorflow]` when the trained model is active, or `[rule-based]`
otherwise.

---

## Project layout

```
gesture_game/
    hand_tracker.py   MediaPipe wrapper → normalized landmark vectors
    classifier.py     Gesture classifier (TensorFlow model + rule-based fallback)
    snake.py          Pure Snake game state machine (no dependencies)
play.py               The game: camera loop, rendering, input handling
collect_data.py       Record labeled gesture samples to a CSV
train.py              Train the TensorFlow model on collected samples
tests/                Unit tests for the game logic and classifier
requirements.txt
```

---

## Tests

The game logic and the rule-based classifier are unit-tested and need only
`numpy` (no camera / MediaPipe / TensorFlow):

```bash
pip install numpy
python -m unittest discover -s tests
```

---

## Troubleshooting

- **"could not open camera"** — try `--camera 1` (or 2). Make sure no other app
  is using the webcam and that camera permissions are granted.
- **Hand not detected** — improve lighting and keep your whole hand in frame;
  the panel shows `no hand` when nothing is found.
- **MediaPipe/TensorFlow install issues** — use Python 3.9–3.11; these wheels
  don't yet cover every newer interpreter on every platform.
