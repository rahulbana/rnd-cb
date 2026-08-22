#!/usr/bin/env python3
"""CLI: build a knowledge graph from .txt files and save it to disk.

Usage:
    python build_graph.py [--data DIR] [--out graph.gml]
"""

import argparse

from graph_rag import config
from graph_rag.graph_store import build_graph, save_graph
from graph_rag.ingest import build_chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the knowledge graph.")
    parser.add_argument(
        "--data", default="data", help="Directory of .txt files (default: data)"
    )
    parser.add_argument(
        "--out",
        default=config.GRAPH_PATH,
        help=f"Output graph file (default: {config.GRAPH_PATH})",
    )
    args = parser.parse_args()

    print(f"Loading and chunking documents from '{args.data}'...")
    chunks = build_chunks(args.data)
    print(f"Got {len(chunks)} chunk(s). Extracting entities/relationships...\n")

    graph = build_graph(chunks)

    print(
        f"\nGraph built: {graph.number_of_nodes()} entities, "
        f"{graph.number_of_edges()} relationships."
    )
    save_graph(graph, args.out)
    print(f"Saved to '{args.out}'. Now run: python query.py")


if __name__ == "__main__":
    main()
