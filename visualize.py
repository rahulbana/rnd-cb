#!/usr/bin/env python3
"""CLI: render the knowledge graph as an interactive HTML page.

Produces a self-contained HTML file (using pyvis / vis.js) that you can open in
any browser. Nodes are draggable, hovering a node shows its type and
description, and hovering an edge shows the relationship.

Usage:
    python visualize.py                       # graph.gml -> graph.html
    python visualize.py --graph g.gml --out viz.html
    python visualize.py --physics             # keep the force layout running
"""

import argparse
import sys

from pyvis.network import Network

from graph_rag import config
from graph_rag.graph_store import load_graph

# A small palette so different entity types are easy to tell apart.
_TYPE_COLORS = {
    "person": "#4C9AFF",
    "organization": "#F78C6B",
    "org": "#F78C6B",
    "place": "#57D9A3",
    "location": "#57D9A3",
    "product": "#C792EA",
    "concept": "#FFD166",
    "event": "#FF6B6B",
}
_DEFAULT_COLOR = "#9AA5B1"


def _color_for(node_type: str) -> str:
    return _TYPE_COLORS.get((node_type or "").strip().lower(), _DEFAULT_COLOR)


def build_visualization(graph, out_path: str, physics: bool) -> None:
    net = Network(
        height="800px",
        width="100%",
        directed=True,
        bgcolor="#1a1a2e",
        font_color="#eaeaea",
        notebook=False,
        # Inline the vis.js library so the HTML is self-contained and works
        # offline (no CDN request needed when you open the file).
        cdn_resources="in_line",
    )

    for node, data in graph.nodes(data=True):
        label = data.get("label", node)
        node_type = data.get("type", "")
        desc = data.get("description", "")
        # Tooltip shown on hover.
        title = label
        if node_type:
            title += f" ({node_type})"
        if desc:
            title += f"\n{desc}"
        # Bigger nodes for more-connected entities.
        degree = graph.degree(node)
        net.add_node(
            node,
            label=label,
            title=title,
            color=_color_for(node_type),
            size=15 + 3 * degree,
        )

    for u, v, data in graph.edges(data=True):
        net.add_edge(u, v, title=data.get("relation", ""), label=data.get("relation", ""))

    net.toggle_physics(physics)
    # Gentle, readable default layout.
    net.set_options(
        """
    var options = {
      "edges": {"color": {"color": "#5c6b7a"}, "font": {"size": 11, "color": "#cfd8e3"},
                "arrows": {"to": {"enabled": true, "scaleFactor": 0.6}}, "smooth": {"type": "dynamic"}},
      "nodes": {"font": {"size": 16}, "borderWidth": 1},
      "physics": {"barnesHut": {"gravitationalConstant": -8000, "springLength": 160},
                  "stabilization": {"iterations": 200}}
    }
    """
    )

    # write_html avoids trying to open a browser (works on headless machines).
    net.write_html(out_path, notebook=False, open_browser=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize the knowledge graph.")
    parser.add_argument(
        "--graph",
        default=config.GRAPH_PATH,
        help=f"Graph file to load (default: {config.GRAPH_PATH})",
    )
    parser.add_argument(
        "--out", default="graph.html", help="Output HTML file (default: graph.html)"
    )
    parser.add_argument(
        "--physics",
        action="store_true",
        help="Keep the force-directed physics running (nodes stay springy).",
    )
    args = parser.parse_args()

    try:
        graph = load_graph(args.graph)
    except FileNotFoundError:
        sys.exit(
            f"Graph file '{args.graph}' not found. Run: python build_graph.py"
        )

    build_visualization(graph, args.out, args.physics)
    print(
        f"Wrote {args.out} "
        f"({graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges). "
        f"Open it in your browser."
    )


if __name__ == "__main__":
    main()
