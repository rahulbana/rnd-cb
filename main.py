from processor import process_docs, process_batch
import os
from vectordb import create_faiss_index, semantic_search, retrieve_relevant_chunks
from embeddings import create_embedding_model
from llm import ask_gemini


def main():
    file_paths = [
        'hesc103.pdf',
        # 'profile.pdf',
        # 'simple_pdf.pdf', 
        # 'test2.xlsx', 
        # 'invoice_image.jpg', 
        # 'Presentation1.pptx',
        # 'sample_text.txt', 
        # 'file-sample_100kB.docx', 
        # 'scannned_pdf.pdf'
    ]
    file_paths = [os.path.join(os.getcwd(), "docs", fp) for fp in file_paths]
    
    print("Processing documents...")
    docs = process_batch(file_paths)
    print("Processing completed")
    index = create_faiss_index(docs)
    print("FAISS index created.")

    model = create_embedding_model()

    query = "What is coal?"
    retrieved = retrieve_relevant_chunks(query, model, index, docs, top_k=4)

    answer = ask_gemini(query, retrieved)
    print("\n🧠 Gemini Answer:\n")
    print(answer)


if __name__ == "__main__":
    main()
    #print(os.listdir("./docs"))
