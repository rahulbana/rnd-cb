# Gesture Control 🖐️

Control your laptop with hand gestures from your webcam — adjust volume, control
media playback, move the mouse, and more, all hands-free.

Built with **Python**, **MediaPipe** (hand tracking on TensorFlow Lite), and a
small **TensorFlow / Keras** classifier.

---

## How it works

```
webcam frame ─▶ MediaPipe hand landmarks ─▶ gesture classifier ─▶ debounce engine ─▶ laptop action
                (21 3D points per hand)      (rules or TF model)   (stabilise/cooldown)  (volume, media, mouse…)
```

1. **OpenCV** grabs frames from the webcam.
2. **MediaPipe Hands** detects 21 hand landmarks (a TensorFlow-Lite model).
3. A **classifier** turns those landmarks into a named gesture. There are two:
   - a built-in **rule-based** recogniser (geometry of the fingers) that works
     immediately with no training, and
   - an optional **TensorFlow MLP** you can train on your own samples for more
     gestures or better accuracy. When a trained model is present the app uses
     it automatically.
4. A **debounce engine** requires a gesture to be stable for several frames and
   rate-limits actions, so nothing fires by accident.
5. A **cross-platform controller** performs the mapped laptop action.

---

## Default gestures

| Gesture       | Hand pose                     | Action              |
|---------------|-------------------------------|---------------------|
| ✋ Open palm   | all five fingers extended     | **Mouse mode** — move cursor with your hand |
| ✊ Fist        | all fingers curled            | **Play / pause** media |
| ☝️ Point       | index finger only             | **Left click**      |
| ✌️ Peace       | index + middle extended       | **Next track**      |
| 👍 Thumbs up   | thumb up, others curled       | **Volume up**       |
| 👎 Thumbs down | thumb down, others curled     | **Volume down**     |
| 🤏 Pinch       | thumb tip touches index tip   | **Mute / unmute**   |

All mappings live in [`config.py`](config.py) under `GESTURE_ACTIONS` — edit them
to taste. Available actions include `volume_up`, `volume_down`, `mute`,
`play_pause`, `next_track`, `prev_track`, `brightness_up`, `brightness_down`,
`mouse_mode`, and `left_click`.

---

## Install

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Platform notes**

- **Windows** — works out of the box.
- **macOS** — grant your terminal *Camera*, *Accessibility*, and *Screen
  Recording* permissions (System Settings → Privacy & Security).
- **Linux** — needs a display server for `pyautogui`. You may also need
  `sudo apt install scrot python3-tk python3-dev`. Screen brightness on laptops
  requires access to `/sys/class/backlight`.

---

## Run

```bash
python main.py                 # use the best available classifier
python main.py --rules         # force the rule-based classifier
python main.py --no-window     # headless (no preview window)
python main.py --camera 1      # pick a different webcam
```

Show your hand to the camera. The preview window displays the detected gesture,
the mapped action, and the current FPS. Press **`q`** or **Esc** (or `Ctrl+C`)
to quit.

---

## Train your own TensorFlow model (optional)

The rule-based recogniser is good enough for the built-in gestures, but you can
train a model for higher accuracy or to add your own gestures.

**1. Collect samples** for each gesture (a few hundred each, from slightly
different angles/distances). Don't forget the `none` class for a relaxed hand:

```bash
python -m train.collect_data --gesture thumbs_up --samples 300
python -m train.collect_data --gesture peace     --samples 300
python -m train.collect_data --gesture none      --samples 300
# … repeat for every gesture in config.GESTURES
```

Samples are appended to `data/landmarks.csv`. Press **SPACE** to pause/resume,
**`q`** to stop.

**2. Train** the classifier:

```bash
python -m train.train_model --epochs 60
```

This writes `models/gesture_model.keras`. The next time you run `python main.py`
it loads the trained model automatically.

To add a brand-new gesture: add its label to `GESTURES` and a mapping in
`GESTURE_ACTIONS` in `config.py`, collect data for it, and retrain.

---

## Project layout

```
.
├── main.py                     # entry point / camera loop
├── config.py                   # all settings + gesture→action mapping
├── requirements.txt
├── src/
│   ├── hand_tracker.py         # MediaPipe hand-landmark detection
│   ├── rule_gestures.py        # geometric (no-training) gesture recogniser
│   ├── gesture_classifier.py   # TensorFlow/Keras classifier + model builder
│   ├── engine.py               # stability/debounce + action dispatch
│   ├── controller.py           # cross-platform laptop actions
│   └── utils.py                # landmark normalisation, FPS meter
├── train/
│   ├── collect_data.py         # record landmark samples per gesture
│   └── train_model.py          # train + save the TF model
├── data/                       # collected training CSV lands here
└── models/                     # trained model lands here
```

---

## Tuning

Everything tweakable is in `config.py`:

- **Camera** — index, resolution, mirroring, whether to show the window.
- **Detection** — MediaPipe confidence thresholds, max hands.
- **Responsiveness** — `STABLE_FRAMES` (how long a gesture must hold before it
  fires), `ACTION_COOLDOWN`, `MIN_CONFIDENCE`.
- **Mouse mode** — `MOUSE_SMOOTHING` and `MOUSE_ACTIVE_MARGIN`.
- **Repeatable actions** — which actions repeat while held (e.g. volume).

---

## Troubleshooting

- **"could not open camera"** — another app may be using the webcam, or the
  index is wrong. Try `--camera 1`.
- **Actions log but nothing happens** — `pyautogui`/`screen-brightness-control`
  may be missing or lack OS permissions. The app degrades gracefully and prints
  what it *would* have done; install the deps and grant permissions.
- **Gesture not recognised well** — improve lighting, keep your whole hand in
  frame, or train the TensorFlow model for your own hand.
