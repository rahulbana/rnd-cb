"""Build, persist, and load the knowledge graph with NetworkX.

Nodes are entities. Edges are relationships. Every node and edge remembers
which source chunk it came from, so retrieval can cite evidence.

We normalize entity names to lowercase for matching, but keep a human-readable
label on each node for display.
"""

import networkx as nx

from . import config
from .extract import extract_from_chunk
from .ingest import Chunk


def _key(name: str) -> str:
    """Canonical key used to match the same entity across chunks."""
    return name.strip().lower()


def build_graph(chunks: list[Chunk], client=None) -> nx.MultiDiGraph:
    """Run extraction over every chunk and assemble a directed graph.

    A MultiDiGraph lets two entities have several distinct relationships
    (e.g. A "founded" B and A "invested in" B) without collisions.
    """
    graph = nx.MultiDiGraph()

    for i, chunk in enumerate(chunks, start=1):
        print(f"  [{i}/{len(chunks)}] extracting from {chunk.source}#{chunk.index}")
        result = extract_from_chunk(chunk, client=client)

        for ent in result["entities"]:
            name = (ent.get("name") or "").strip()
            if not name:
                continue
            key = _key(name)
            if graph.has_node(key):
                node = graph.nodes[key]
                # Enrich an existing node without overwriting good data.
                if not node.get("description") and ent.get("description"):
                    node["description"] = ent["description"]
                node["sources"] = _add(node.get("sources", ""), _source_tag(chunk))
            else:
                graph.add_node(
                    key,
                    label=name,
                    type=ent.get("type", "") or "",
                    description=ent.get("description", "") or "",
                    sources=_source_tag(chunk),
                )

        for rel in result["relationships"]:
            src = _key(rel.get("source", ""))
            tgt = _key(rel.get("target", ""))
            relation = (rel.get("relation") or "").strip()
            if not src or not tgt or not relation:
                continue
            # Make sure both endpoints exist even if only named in a relation.
            for endpoint, raw in ((src, rel["source"]), (tgt, rel["target"])):
                if not graph.has_node(endpoint):
                    graph.add_node(
                        endpoint,
                        label=raw.strip(),
                        type="",
                        description="",
                        sources=_source_tag(chunk),
                    )
            graph.add_edge(src, tgt, relation=relation, source=_source_tag(chunk))

    return graph


def _source_tag(chunk: Chunk) -> str:
    return f"{chunk.source}#{chunk.index}"


def _add(existing: str, new: str) -> str:
    """Append a source tag to a comma-separated list, avoiding duplicates."""
    parts = [p for p in existing.split(",") if p]
    if new not in parts:
        parts.append(new)
    return ",".join(parts)


def save_graph(graph: nx.MultiDiGraph, path: str = config.GRAPH_PATH) -> None:
    """Persist the graph to disk in GML format."""
    nx.write_gml(graph, path)


def load_graph(path: str = config.GRAPH_PATH) -> nx.MultiDiGraph:
    """Load a previously built graph from disk."""
    return nx.read_gml(path)
