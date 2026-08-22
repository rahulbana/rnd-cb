"""Graph-only retrieval.

Steps:
  1. Ask the LLM which entities the question is about.
  2. Match those entities to nodes in the graph (exact, then fuzzy substring).
  3. Walk `depth` hops out from each matched node, collecting the relationships
     (edges) along the way.
  4. Format the collected relationships into a text context block.

No vector store is involved — the graph structure itself is the index.
"""

import json

import networkx as nx

from . import config


def extract_query_entities(question: str, client=None) -> list[str]:
    """Ask the LLM for the key entities mentioned in the question."""
    client = client or config.get_client()
    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract the key named entities from the user's question. "
                    'Return JSON: {"entities": ["name", ...]}. '
                    "Include people, organizations, places, products, and "
                    "concepts. Return an empty list if none are present."
                ),
            },
            {"role": "user", "content": question},
        ],
    )
    try:
        data = json.loads(response.choices[0].message.content)
        return [e for e in data.get("entities", []) if e]
    except (json.JSONDecodeError, AttributeError):
        return []


def match_nodes(graph: nx.MultiDiGraph, names: list[str]) -> list[str]:
    """Map entity names to node keys in the graph (exact then substring)."""
    matched: list[str] = []
    node_keys = list(graph.nodes)

    for name in names:
        key = name.strip().lower()
        if graph.has_node(key):
            matched.append(key)
            continue
        # Fuzzy fallback: substring match either direction.
        for node_key in node_keys:
            if key in node_key or node_key in key:
                matched.append(node_key)

    # Preserve order, drop duplicates.
    seen: set[str] = set()
    unique = []
    for k in matched:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


def _neighborhood(graph: nx.MultiDiGraph, start: str, depth: int) -> set[str]:
    """Return start plus all nodes within `depth` hops (either direction)."""
    undirected = graph.to_undirected(as_view=True)
    nodes = {start}
    frontier = {start}
    for _ in range(depth):
        nxt: set[str] = set()
        for node in frontier:
            nxt.update(undirected.neighbors(node))
        nodes.update(nxt)
        frontier = nxt
    return nodes


def gather_context(
    graph: nx.MultiDiGraph,
    matched: list[str],
    depth: int = config.TRAVERSAL_DEPTH,
) -> tuple[str, list[str]]:
    """Collect relationships around the matched nodes into a context string.

    Returns (context_text, sources).
    """
    if not matched:
        return "", []

    relevant: set[str] = set()
    for node in matched:
        relevant |= _neighborhood(graph, node, depth)

    facts: list[str] = []
    sources: set[str] = set()

    # Node descriptions give the model background on each entity.
    for node in sorted(relevant):
        data = graph.nodes[node]
        label = data.get("label", node)
        desc = data.get("description", "")
        if desc:
            facts.append(f"- {label} ({data.get('type', 'entity')}): {desc}")
        for tag in data.get("sources", "").split(","):
            if tag:
                sources.add(tag)

    # Edges among the relevant nodes are the actual relationship facts.
    for u, v, data in graph.edges(data=True):
        if u in relevant and v in relevant:
            u_label = graph.nodes[u].get("label", u)
            v_label = graph.nodes[v].get("label", v)
            facts.append(f"- {u_label} --[{data['relation']}]--> {v_label}")
            if data.get("source"):
                sources.add(data["source"])

    return "\n".join(facts), sorted(sources)


def retrieve(question: str, graph: nx.MultiDiGraph, client=None):
    """Full retrieval: question -> matched entities -> context.

    Returns a dict with the intermediate results so callers (and learners) can
    inspect exactly what the graph contributed.
    """
    client = client or config.get_client()
    query_entities = extract_query_entities(question, client=client)
    matched = match_nodes(graph, query_entities)
    context, sources = gather_context(graph, matched)
    return {
        "query_entities": query_entities,
        "matched_nodes": [graph.nodes[m].get("label", m) for m in matched],
        "context": context,
        "sources": sources,
    }
