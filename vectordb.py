import faiss
import numpy as np

def create_faiss_index(documents):
    """Create a FAISS index from documents that already have embeddings."""
    embeddings = np.array([doc.embedding for doc in documents])
    dim = embeddings.shape[1]

    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    print(f"✅ FAISS index built with {len(documents)} vectors of dimension {dim}")
    return index


def semantic_search(query, model, index, documents, top_k=3):
    """Perform semantic search on FAISS index."""
    query_emb = model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_emb, top_k)

    print("\n🔍 Top Results:")
    for rank, idx in enumerate(indices[0]):
        print(f"\nRank {rank+1} | Distance: {distances[0][rank]:.4f}")
        print(f"→ {documents[idx].text[:400]}...")

def retrieve_relevant_chunks(query, model, index, documents, top_k=3):
    query_emb = model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_emb, top_k)
    retrieved = [documents[i].text for i in indices[0]]
    return retrieved

def create_or_update_faiss_index(documents, INDEX, DOCS):
    """Create or update global FAISS index with new documents."""
    #global INDEX, DOCS

    embeddings = np.array([doc.embedding for doc in documents])
    dim = embeddings.shape[1]

    if INDEX is None:
        INDEX = faiss.IndexFlatL2(dim)
        INDEX.add(embeddings)
    else:
        INDEX.add(embeddings)

    DOCS.extend(documents)
    print(f"✅ FAISS index now has {len(DOCS)} documents.")
    return INDEX, DOCS
