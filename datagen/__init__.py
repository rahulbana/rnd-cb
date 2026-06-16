"""datagen — a configurable synthetic data generation agent.

Generate datasets for classification, regression, clustering, plain tabular
data, and text tasks (text classification / summarization).  You control the
columns, data types, ranges, record counts, and per-column outlier fractions.

Quick start::

    from datagen import DataGenAgent

    spec = {
        "task": "tabular",
        "n_rows": 1000,
        "columns": [
            {"name": "age", "dtype": "int", "min": 18, "max": 90, "outlier_pct": 0.05},
            {"name": "salary", "dtype": "float", "distribution": "normal",
             "mean": 60000, "std": 15000, "outlier_pct": 0.02},
            {"name": "dept", "dtype": "category",
             "categories": ["eng", "sales", "ops"], "weights": [0.5, 0.3, 0.2]},
        ],
    }
    df = DataGenAgent(spec).generate()
"""

from .agent import DataGenAgent, generate
from .spec import ColumnSpec, DatasetSpec, SpecError

__all__ = [
    "DataGenAgent",
    "generate",
    "ColumnSpec",
    "DatasetSpec",
    "SpecError",
]

__version__ = "0.1.0"
