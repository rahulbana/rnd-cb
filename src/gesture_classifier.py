"""TensorFlow/Keras gesture classifier over normalised hand landmarks.

The model is a small fully-connected network that takes the 63 normalised
landmark coordinates (21 points x xyz) and outputs a probability for each
gesture in `config.GESTURES`. Because the input is already a compact,
scale/translation-invariant feature vector, a tiny MLP trains in seconds and
runs comfortably in real time on a CPU.

This module is imported lazily by the app: if TensorFlow is missing or no
trained model exists, the app falls back to the rule-based classifier.
"""

from __future__ import annotations

import os
from typing import Tuple

import numpy as np

import config
from src.utils import normalize_landmarks, landmarks_to_array


def build_model(num_classes: int) -> "tf.keras.Model":
    """Create (but do not train) the MLP classifier."""
    import tensorflow as tf

    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(63,)),
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dropout(0.3),
            tf.keras.layers.Dense(64, activation="relu"),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(num_classes, activation="softmax"),
        ],
        name="gesture_mlp",
    )
    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


class GestureClassifier:
    """Loads a trained Keras model and predicts gestures from landmarks."""

    def __init__(self, model_path: str = config.MODEL_PATH) -> None:
        import tensorflow as tf  # imported here so the app can run without TF

        self._model = tf.keras.models.load_model(model_path)
        self._labels = list(config.GESTURES)

    @classmethod
    def is_available(cls, model_path: str = config.MODEL_PATH) -> bool:
        """True if a trained model file exists on disk."""
        return os.path.exists(model_path)

    def predict(self, landmarks) -> Tuple[str, float]:
        """Return (gesture_label, confidence) for a MediaPipe landmark set."""
        features = normalize_landmarks(landmarks_to_array(landmarks))
        features = features.reshape(1, -1)
        probs = self._model.predict(features, verbose=0)[0]
        idx = int(np.argmax(probs))
        confidence = float(probs[idx])

        if confidence < config.MIN_CONFIDENCE:
            return "none", confidence

        label = self._labels[idx] if idx < len(self._labels) else "none"
        return label, confidence
