"""Schema agent: turn a raw plan into a coherent, buildable schema.

Responsibilities:
* guarantee unique, valid column names,
* add a primary-key ``id`` column when one is absent,
* ensure the target name does not collide with a feature,
* normalise category weights.
"""

from __future__ import annotations

import re

from app.agents.base import Agent
from app.models.spec import DatasetSpec, DType, FeatureRole, FeatureSpec


class SchemaAgent(Agent):
    name = "schema"

    def run(self, spec: DatasetSpec) -> DatasetSpec:
        seen: set[str] = set()
        for feature in spec.features:
            feature.name = self._normalise(feature.name)
            base = feature.name
            n = 2
            while feature.name in seen:
                feature.name = f"{base}_{n}"
                n += 1
            seen.add(feature.name)
            self._normalise_weights(feature)

        # Add a primary key if none present.
        if not any(f.role == FeatureRole.ID for f in spec.features):
            spec.features.insert(
                0,
                FeatureSpec(
                    name="id",
                    dtype=DType.INTEGER,
                    role=FeatureRole.ID,
                    description="Primary key (row identifier)",
                ),
            )

        # Keep the target out of the feature set and free of name clashes.
        if spec.target is not None:
            if spec.target.name in seen:
                spec.target.name = f"{spec.target.name}_label"
        self.log(f"schema finalised with {len(spec.features)} columns")
        return spec

    def _normalise(self, name: str) -> str:
        name = re.sub(r"[^0-9a-zA-Z_]+", "_", name.strip()).strip("_").lower()
        if not name:
            name = "feature"
        if name[0].isdigit():
            name = f"f_{name}"
        return name

    def _normalise_weights(self, feature: FeatureSpec) -> None:
        if feature.weights:
            total = float(sum(feature.weights))
            if total > 0:
                feature.weights = [w / total for w in feature.weights]
