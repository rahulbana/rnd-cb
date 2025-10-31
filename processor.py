import os
from text_extractor import TextExtractor
from visual_extractor import VisualExtractor
from chunking import recursive_chunk_pdf
from embeddings import embed_documents


def process_docs(file_path: str):

    ext = os.path.splitext(file_path)[1].lower()
    print(f"File extension: {ext}")

    if ext == '.txt':
        extractor = TextExtractor()
        docs = extractor.extract(file_path)
        return docs
    else:
        extractor = VisualExtractor()
        docs = extractor.extract(file_path)
        return docs

def process_batch(file_paths: list):
    all_docs = []
    for file_path in file_paths:
        print(f"Processing file: {file_path}")
        res = process_docs(file_path)
        chunks = recursive_chunk_pdf(res)
        all_docs.extend(chunks)
        print(f"Processing for file: {file_path} completed.")

    all_docs = embed_documents(all_docs)
    return all_docs