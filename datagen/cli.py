"""Command-line interface for the datagen agent.

Examples::

    # Generate from a spec file
    python -m datagen.cli generate examples/classification.json -o out.csv

    # Quick tabular generation without writing a spec file
    python -m datagen.cli quick --rows 500 --task regression --features 8 -o reg.csv

    # Inspect what a spec would produce (prints first rows + summary)
    python -m datagen.cli preview examples/text_classification.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import DataGenAgent
from .spec import DatasetSpec, SpecError


def _print_summary(df, n: int = 5) -> None:
    print(df.head(n).to_string(index=False))
    print(f"\n[{len(df)} rows x {len(df.columns)} columns]")
    print("dtypes:")
    for col, dt in df.dtypes.items():
        print(f"  {col}: {dt}")


def _cmd_generate(args: argparse.Namespace) -> int:
    agent = DataGenAgent.from_file(args.spec)
    out = agent.to_file(args.output, fmt=args.format)
    print(f"Wrote {out}")
    if args.preview:
        import pandas as pd  # local import keeps startup fast

        _print_summary(agent.generate())
    return 0


def _cmd_preview(args: argparse.Namespace) -> int:
    agent = DataGenAgent.from_file(args.spec)
    _print_summary(agent.generate(), n=args.rows)
    return 0


def _cmd_quick(args: argparse.Namespace) -> int:
    spec_dict: dict = {
        "task": args.task,
        "n_rows": args.rows,
        "seed": args.seed,
    }
    if args.task in {"classification", "regression", "clustering"}:
        spec_dict["n_features"] = args.features
        spec_dict["feature_outlier_pct"] = args.outliers
        if args.task == "classification":
            spec_dict["n_classes"] = args.classes
        if args.task == "clustering":
            spec_dict["n_clusters"] = args.clusters
    elif args.task == "tabular":
        # A small illustrative schema; real use should pass a spec file.
        spec_dict["columns"] = [
            {"name": "x", "dtype": "float", "distribution": "normal",
             "mean": 0, "std": 1, "outlier_pct": args.outliers},
            {"name": "y", "dtype": "int", "min": 0, "max": 100},
            {"name": "group", "dtype": "category", "categories": ["a", "b", "c"]},
        ]
    elif args.task in {"text_classification", "summarization"}:
        pass  # text tasks use defaults

    agent = DataGenAgent(spec_dict)
    out = agent.to_file(args.output, fmt=args.format)
    print(f"Wrote {out}")
    if args.preview:
        _print_summary(agent.generate())
    return 0


def _cmd_examples(args: argparse.Namespace) -> int:
    """Dump bundled example specs to a directory."""
    src = Path(__file__).resolve().parent.parent / "examples"
    if not src.exists():
        print("No bundled examples directory found.", file=sys.stderr)
        return 1
    for f in sorted(src.glob("*.json")):
        print(f"{f.name}:")
        print(f.read_text())
        print("-" * 60)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="datagen",
        description="Generate synthetic data for ML and text projects.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="Generate data from a spec file.")
    g.add_argument("spec", help="Path to a JSON/YAML spec file.")
    g.add_argument("-o", "--output", default="output.csv", help="Output file path.")
    g.add_argument("-f", "--format", default=None, help="csv|json|jsonl|parquet.")
    g.add_argument("--preview", action="store_true", help="Print a sample.")
    g.set_defaults(func=_cmd_generate)

    p = sub.add_parser("preview", help="Preview a spec without writing files.")
    p.add_argument("spec", help="Path to a JSON/YAML spec file.")
    p.add_argument("-n", "--rows", type=int, default=5, help="Rows to display.")
    p.set_defaults(func=_cmd_preview)

    q = sub.add_parser("quick", help="Generate quickly from flags.")
    q.add_argument("--task", default="classification",
                   choices=["tabular", "classification", "regression",
                            "clustering", "text_classification", "summarization"])
    q.add_argument("--rows", type=int, default=200)
    q.add_argument("--features", type=int, default=5)
    q.add_argument("--classes", type=int, default=3)
    q.add_argument("--clusters", type=int, default=3)
    q.add_argument("--outliers", type=float, default=0.0,
                   help="Fraction of outliers in feature columns (0..1).")
    q.add_argument("--seed", type=int, default=None)
    q.add_argument("-o", "--output", default="output.csv")
    q.add_argument("-f", "--format", default=None)
    q.add_argument("--preview", action="store_true")
    q.set_defaults(func=_cmd_quick)

    e = sub.add_parser("examples", help="Print bundled example specs.")
    e.set_defaults(func=_cmd_examples)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (SpecError, ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
