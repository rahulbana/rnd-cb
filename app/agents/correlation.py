"""Correlation agent: impose realistic dependencies between numeric features.

For every :class:`CorrelationSpec` the target column is rewritten as a linear
blend of the (standardised) source and its own noise, then rescaled back to its
original mean and standard deviation. This reproduces relationships such as
``income -> loan_amount`` or ``age -> salary`` while preserving each column's
marginal scale.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.agents.base import Agent
from app.models.spec import DatasetSpec, DType


class CorrelationAgent(Agent):
    name = "correlation"

    def run(
        self, df: pd.DataFrame, spec: DatasetSpec, rng: np.random.Generator
    ) -> pd.DataFrame:
        applied = 0
        for corr in spec.correlations:
            if corr.source not in df.columns or corr.target not in df.columns:
                continue
            src = df[corr.source].astype(float)
            tgt = df[corr.target].astype(float)
            if src.std() == 0 or tgt.std() == 0:
                continue

            src_z = (src - src.mean()) / src.std()
            r = float(np.clip(corr.strength, -1.0, 1.0))
            noise = rng.normal(0, 1, len(df))
            blended = r * src_z + np.sqrt(max(0.0, 1 - r**2)) * noise
            # Rescale to the original marginal of the target.
            new_values = blended * tgt.std() + tgt.mean()

            target_spec = spec.get_feature(corr.target)
            if target_spec is not None:
                if target_spec.low is not None:
                    new_values = np.maximum(new_values, target_spec.low)
                if target_spec.high is not None:
                    new_values = np.minimum(new_values, target_spec.high)
                if target_spec.dtype == DType.INTEGER:
                    new_values = np.round(new_values)
            df[corr.target] = new_values
            applied += 1

        if applied:
            self.log(f"applied {applied} correlation(s)")
        return df
