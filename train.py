#!/usr/bin/env python3
"""Train the TensorFlow gesture classifier on collected landmark data.

Reads the CSV produced by ``collect_data.py`` and trains a small fully-connected
Keras network that maps a 42-dim landmark vector to one of the five gesture
classes. The trained model is saved to ``models/gesture_model.keras`` where
``play.py`` picks it up automatically.

Usage::

    python train.py                        # defaults
    python train.py --epochs 80 --data data/gestures.csv
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional, Tuple

import numpy as np

from gesture_game.classifier import GESTURES
from gesture_game.hand_tracker import FEATURE_DIM


def load_dataset(path: str) -> Tuple[np.ndarray, np.ndarray]:
    """Load features/labels from the CSV, skipping the header row."""
    import csv

    label_to_id = {g: i for i, g in enumerate(GESTURES)}
    X: List[List[float]] = []
    y: List[int] = []
    with open(path, newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        for row in reader:
            if not row:
                continue
            label = row[0]
            if label not in label_to_id:
                continue
            feats = [float(v) for v in row[1:]]
            if len(feats) != FEATURE_DIM:
                continue
            X.append(feats)
            y.append(label_to_id[label])
    return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.int64)


def build_model():
    import tensorflow as tf

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(FEATURE_DIM,)),
        tf.keras.layers.Dense(128, activation="relu"),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(len(GESTURES), activation="softmax"),
    ])
    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Train the gesture classifier.")
    parser.add_argument("--data", default="data/gestures.csv")
    parser.add_argument("--out", default="models/gesture_model.keras")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--val-split", type=float, default=0.2)
    args = parser.parse_args(argv)

    if not os.path.exists(args.data):
        print(f"Error: no dataset at '{args.data}'. Run collect_data.py first.",
              file=sys.stderr)
        return 1

    X, y = load_dataset(args.data)
    if len(X) == 0:
        print("Error: dataset is empty.", file=sys.stderr)
        return 1

    counts = {GESTURES[i]: int((y == i).sum()) for i in range(len(GESTURES))}
    print(f"[train] Loaded {len(X)} samples: {counts}")
    if min(counts.values()) == 0:
        print("[train] Warning: some classes have no samples; collect more data "
              "for balanced results.")

    # Shuffle before the (stratified-ish) split done by Keras validation_split.
    rng = np.random.default_rng(42)
    perm = rng.permutation(len(X))
    X, y = X[perm], y[perm]

    import tensorflow as tf

    model = build_model()
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=10, restore_best_weights=True
        ),
    ]
    model.fit(
        X, y,
        epochs=args.epochs,
        batch_size=args.batch_size,
        validation_split=args.val_split,
        callbacks=callbacks,
        verbose=2,
    )

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    model.save(args.out)
    print(f"[train] Saved model to {args.out}")
    print("[train] Run 'python play.py' to play with the trained model.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
