"""
Train the TensorFlow gesture classifier on collected landmark data.

Reads the CSV produced by train/collect_data.py, trains the small MLP defined in
src/gesture_classifier.py, and saves the result to config.MODEL_PATH. Once the
model exists, main.py picks it up automatically.

Usage:
    python -m train.train_model
    python -m train.train_model --epochs 80 --batch-size 32
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

import config
from src.gesture_classifier import build_model


def load_dataset(path: str):
    """Load the CSV into (X, y) arrays. First column is the integer label."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No dataset at {path}. Run `python -m train.collect_data --gesture <name>` first."
        )
    data = np.loadtxt(path, delimiter=",", skiprows=1, dtype=np.float32)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    y = data[:, 0].astype(np.int64)
    X = data[:, 1:]
    if X.shape[1] != 63:
        raise ValueError(f"Expected 63 features per row, got {X.shape[1]}.")
    return X, y


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the gesture classifier.")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--val-split", type=float, default=0.2)
    args = parser.parse_args()

    import tensorflow as tf

    X, y = load_dataset(config.DATA_PATH)
    num_classes = len(config.GESTURES)

    present = sorted(set(int(v) for v in y))
    print(f"[train] loaded {len(X)} samples across labels {present} "
          f"(of {num_classes} configured gestures).")
    if len(present) < 2:
        print("[train] WARNING: need at least two different gestures to train a "
              "useful classifier. Collect more data.")

    # Shuffle before the validation split so classes are mixed.
    rng = np.random.default_rng(42)
    perm = rng.permutation(len(X))
    X, y = X[perm], y[perm]

    model = build_model(num_classes)
    model.summary()

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=10, restore_best_weights=True
        ),
    ]

    model.fit(
        X, y,
        validation_split=args.val_split,
        epochs=args.epochs,
        batch_size=args.batch_size,
        callbacks=callbacks,
        verbose=2,
    )

    os.makedirs(os.path.dirname(config.MODEL_PATH), exist_ok=True)
    model.save(config.MODEL_PATH)
    print(f"[train] saved model -> {config.MODEL_PATH}")
    print("[train] run `python main.py` to use it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
