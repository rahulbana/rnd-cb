# Graph RAG (learning project)

A minimal, readable **Graph RAG** implementation in Python using OpenAI. It's
built for learning: every stage is a small module you can read top to bottom.

Instead of the usual "embed chunks → vector search" RAG, this project builds a
**knowledge graph** from your documents and answers questions by **traversing
the graph** — no vector store involved. That makes the retrieval logic fully
visible: you can see exactly which entities and relationships fed each answer.

## How it works

```
Build:  .txt files ──chunk──▶ LLM entity/relation extraction ──▶ NetworkX graph ──▶ graph.gml

Query:  question ──▶ LLM finds entities ──▶ match graph nodes ──▶ walk N hops
                 ──▶ collect relationship facts ──▶ LLM writes the answer
```

- **Store:** NetworkX `MultiDiGraph`, in memory, saved to `graph.gml`.
- **Source:** plain `.txt` files in `data/`.
- **Retrieval:** graph-only traversal (entities → neighborhood → facts).
- **Interface:** two CLI scripts.

## Project layout

| File | Purpose |
|------|---------|
| `graph_rag/config.py` | Settings + shared OpenAI client |
| `graph_rag/ingest.py` | Load `.txt`, split into overlapping chunks |
| `graph_rag/extract.py` | LLM extraction of entities & relationships (JSON mode) |
| `graph_rag/graph_store.py` | Build / save / load the NetworkX graph |
| `graph_rag/retrieve.py` | Question → entities → graph traversal → context |
| `graph_rag/answer.py` | Turn graph facts into a final answer |
| `build_graph.py` | CLI to build the graph |
| `query.py` | CLI to ask questions |
| `visualize.py` | CLI to render the graph as interactive HTML |
| `data/` | Sample documents (swap in your own `.txt`) |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # then edit .env and add your OPENAI_API_KEY
```

## Usage

Build the graph from the sample data (or your own `.txt` files in `data/`):

```bash
python build_graph.py
```

Ask questions:

```bash
# interactive REPL
python query.py

# one-shot
python query.py "Who created AlphaGo and what did it achieve?"

# see the exact graph facts used to answer
python query.py --show-context "How is NVIDIA connected to OpenAI?"
```

## Visualize the graph

Render the built graph as an interactive page and open it in your browser:

```bash
python visualize.py                 # writes graph.html
python visualize.py --physics       # keep the springy force layout live
```

`graph.html` is self-contained (the vis.js library is inlined, so it works
offline). Nodes are draggable and colored by entity type; hover a node to see
its description, hover an edge to see the relationship. Bigger nodes are more
connected.

### Example questions for the sample data

- "Who is considered the first computer programmer and why?"
- "How is Microsoft connected to OpenAI?"
- "Which companies rely on NVIDIA GPUs?"
- "What did Alan Turing work on during World War II?"

## Using your own data

Drop `.txt` files into `data/` (delete the samples if you like), then rerun
`python build_graph.py`. Tuning knobs live in `.env` / `graph_rag/config.py`:

- `OPENAI_MODEL` — extraction/answering model (default `gpt-4o-mini`).
- `CHUNK_SIZE`, `CHUNK_OVERLAP` — how documents are split.
- `TRAVERSAL_DEPTH` — how many hops out from a matched entity to gather context
  (increase to 2 for broader, multi-hop answers).

## Ideas to extend it

- Add embeddings for **hybrid** retrieval (semantic + graph).
- Add community detection + summaries (Microsoft-style GraphRAG).
- Swap NetworkX for **Neo4j** behind the `graph_store` interface.
- Visualize the graph (e.g. `pyvis`).
