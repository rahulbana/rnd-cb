# datagen — synthetic data generation agent

`datagen` is a configurable agent for generating synthetic datasets for your
projects. You control the task, the columns, their data types and ranges, the
number of records, and what fraction of each column is outliers. It also
generates **text** datasets for text classification and summarization.

It depends only on **NumPy** and **pandas** — no model downloads, fully
reproducible via a seed.

## Capabilities

| Task | What you get |
| --- | --- |
| `tabular` | Columns you fully specify (numeric, category, bool, datetime, text, uuid, name, email) |
| `classification` | Numeric features with class-conditional clusters + a label |
| `regression` | Numeric features + a continuous target from a linear model |
| `clustering` | Gaussian blobs + ground-truth cluster id |
| `text_classification` | `(text, label)` pairs with a recoverable topic/sentiment signal |
| `summarization` | `(document, summary)` pairs |

You decide:

- **Number of records** — `n_rows`
- **Number of columns, their data type and range** — the `columns` list
- **Outlier percentage per column** — `outlier_pct` (and `feature_outlier_pct`
  for auto-generated feature columns)
- **Null percentage per column** — `null_pct`
- **Distributions** — `uniform`, `normal`, `lognormal`, `exponential`
- **Reproducibility** — `seed`

## Install

```bash
pip install -r requirements.txt      # numpy + pandas
# optional: pip install pyyaml pyarrow   # YAML specs / Parquet output
```

Or install the package (adds a `datagen` console command):

```bash
pip install -e .
```

## Quick start (Python)

```python
from datagen import DataGenAgent

spec = {
    "task": "tabular",
    "n_rows": 1000,
    "seed": 42,
    "columns": [
        {"name": "age", "dtype": "int", "min": 18, "max": 90, "outlier_pct": 0.05},
        {"name": "salary", "dtype": "float", "distribution": "normal",
         "mean": 60000, "std": 15000, "outlier_pct": 0.02},
        {"name": "department", "dtype": "category",
         "categories": ["eng", "sales", "ops"], "weights": [0.5, 0.3, 0.2]},
        {"name": "is_active", "dtype": "bool", "p_true": 0.8},
        {"name": "joined_at", "dtype": "datetime",
         "min": "2018-01-01", "max": "2025-01-01"},
        {"name": "bio", "dtype": "text", "text_words": [10, 30], "null_pct": 0.1},
    ],
}

df = DataGenAgent(spec).generate()       # -> pandas.DataFrame
DataGenAgent(spec).to_file("people.csv") # csv | json | jsonl | parquet
```

### ML tasks

```python
# Classification: 6 features, 3 named classes, 3% outliers in features
df = DataGenAgent({
    "task": "classification",
    "n_rows": 1000,
    "n_features": 6,
    "n_classes": 3,
    "class_names": ["low", "medium", "high"],
    "cluster_std": 1.5,
    "feature_outlier_pct": 0.03,
    "seed": 1,
}).generate()
```

### Text tasks

```python
# Text classification with a recoverable topic signal
df = DataGenAgent({
    "task": "text_classification",
    "n_rows": 800,
    "text": {"flavor": "topic",
             "labels": ["finance", "sports", "technology", "health"]},
}).generate()  # columns: text, label
```

`flavor` can be `"topic"` (finance / sports / technology / health / politics)
or `"sentiment"` (positive / negative / neutral).

## Command line

```bash
# Generate from a spec file
python -m datagen.cli generate examples/classification.json -o out.csv --preview

# Preview a spec without writing files
python -m datagen.cli preview examples/text_classification.json -n 5

# Generate quickly from flags (no spec file needed)
python -m datagen.cli quick --task regression --rows 500 --features 8 \
    --outliers 0.02 -o reg.csv

# Print the bundled example specs
python -m datagen.cli examples
```

Output format is inferred from the file extension (`.csv`, `.json`, `.jsonl`,
`.parquet`) or set with `-f/--format`.

## Spec reference

### Dataset-level keys

| Key | Default | Notes |
| --- | --- | --- |
| `task` | `tabular` | see capability table above |
| `n_rows` | `100` | number of records |
| `columns` | `[]` | feature columns (required for `tabular`; optional extras for ML tasks) |
| `n_features` | `5` | auto-generated numeric features (ML tasks) |
| `n_classes` | `2` | classification only |
| `n_clusters` | `3` | clustering only |
| `cluster_std` | `1.0` | spread of clusters/classes |
| `noise` | `1.0` | regression target noise |
| `n_informative` | all | informative features (regression) |
| `class_names` | `null` | human-readable labels (classification) |
| `target_name` | `target` | name of the generated label/target column |
| `feature_outlier_pct` | `0.0` | outlier fraction for auto features |
| `text` | `{}` | text-task options (`flavor`, `labels`, `words`, ...) |
| `seed` | `null` | RNG seed for reproducibility |

### Column-level keys

| Key | Applies to | Notes |
| --- | --- | --- |
| `name` | all | required |
| `dtype` | all | `int`, `float`, `category`, `bool`, `datetime`, `text`, `uuid`, `name`, `email` |
| `distribution` | numeric | `uniform`, `normal`, `lognormal`, `exponential` |
| `min` / `max` | numeric, datetime | range / clip bounds (datetime accepts date strings) |
| `mean` / `std` | numeric | for `normal`/`lognormal`; `mean` is the scale for `exponential` |
| `categories` / `weights` | category | allowed values + optional sampling weights |
| `p_true` | bool | probability of `True` |
| `decimals` | float | rounding precision |
| `datetime_format` | datetime | `strftime` format (omit for raw timestamps) |
| `outlier_pct` | all | fraction (0..1) replaced by outliers |
| `null_pct` | all | fraction (0..1) set to null |
| `text_words` | text | `[min, max]` word count |

Outliers: numeric columns get values pushed 4–8 spreads beyond the data
(alternating high/low); non-numeric columns get an out-of-vocabulary
`__OUTLIER__` sentinel.

## Examples

Ready-to-run specs live in [`examples/`](examples/): `classification.json`,
`regression.json`, `clustering.json`, `tabular.json`,
`text_classification.json`, `summarization.json`.

## Tests

```bash
pip install pytest
python -m pytest tests/ -q
```
