#!/usr/bin/env python3
"""CLI: ask questions against the knowledge graph.

Usage:
    python query.py                      # interactive REPL
    python query.py "your question"      # single question
    python query.py --graph graph.gml --show-context "your question"
"""

import argparse
import sys

from graph_rag import config
from graph_rag.answer import generate_answer
from graph_rag.graph_store import load_graph
from graph_rag.retrieve import retrieve


def answer_once(question: str, graph, client, show_context: bool) -> None:
    result = retrieve(question, graph, client=client)

    print(f"\nEntities in question : {result['query_entities']}")
    print(f"Matched graph nodes  : {result['matched_nodes']}")
    if show_context:
        print("\n--- graph context ---")
        print(result["context"] or "(none)")
        print("--- end context ---")

    reply = generate_answer(question, result["context"], client=client)
    print(f"\nAnswer:\n{reply}")
    if result["sources"]:
        print(f"\nSources: {', '.join(result['sources'])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the knowledge graph.")
    parser.add_argument("question", nargs="*", help="Question (omit for REPL).")
    parser.add_argument(
        "--graph",
        default=config.GRAPH_PATH,
        help=f"Graph file to load (default: {config.GRAPH_PATH})",
    )
    parser.add_argument(
        "--show-context",
        action="store_true",
        help="Print the graph facts used to answer.",
    )
    args = parser.parse_args()

    try:
        graph = load_graph(args.graph)
    except FileNotFoundError:
        sys.exit(
            f"Graph file '{args.graph}' not found. Run: python build_graph.py"
        )

    client = config.get_client()
    print(
        f"Loaded graph: {graph.number_of_nodes()} entities, "
        f"{graph.number_of_edges()} relationships."
    )

    if args.question:
        answer_once(" ".join(args.question), graph, client, args.show_context)
        return

    print("Interactive mode. Type a question, or 'quit' to exit.")
    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"quit", "exit", "q"}:
            break
        if question:
            answer_once(question, graph, client, args.show_context)


if __name__ == "__main__":
    main()
