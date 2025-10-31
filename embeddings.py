from sentence_transformers import SentenceTransformer


def create_embedding_model(model_name: str = "all-MiniLM-L6-v2"):
    """
    Create and return a sentence transformer embedding model.
    
    Args:
        model_name (str): The name of the pre-trained model to load.
        
    Returns:
        SentenceTransformer: The loaded embedding model.
    """
    model = SentenceTransformer(model_name)
    return model


def embed_documents(documents):
    """
    Generate embeddings for a list of texts using the provided model.
    """
    model = create_embedding_model()

    texts = [doc.text for doc in documents]
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    for doc, emb in zip(documents, embeddings):
        doc.embedding = emb  # attach embedding to each Document

    return documents


