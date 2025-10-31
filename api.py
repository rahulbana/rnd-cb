from dotenv import load_dotenv
load_dotenv()

import traceback
from pydantic import BaseModel
from processor import process_docs, process_batch
import os
from vectordb import create_faiss_index, semantic_search, retrieve_relevant_chunks, create_or_update_faiss_index
from embeddings import create_embedding_model
from llm import ask_gemini
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import tempfile

# ----------------------------
# Global Setup
# ----------------------------
app = FastAPI(title="📄 Document RAG API with Gemini + FAISS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class QuestionRequest(BaseModel):
    question: str

# Keep global FAISS index + model in memory
MODEL = create_embedding_model()
INDEX = None
DOCS = []


@app.post("/upload")
async def upload_document(file: UploadFile):
    """Upload a PDF and index it."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        global INDEX, DOCS
        docs = process_batch([tmp_path])
        #INDEX = create_faiss_index(docs)
        INDEX, DOCS = create_or_update_faiss_index(docs, INDEX, DOCS)
        # text = clean_pdf_text(tmp_path)
        # docs = chunk_text(text, pdf_path=file.filename)
        # docs = embed_documents(docs)
        # create_or_update_faiss_index(docs)
        return JSONResponse({"status": "success", "chunks_added": len(docs)})
    except Exception as e:
        error_msg = traceback.format_exc()
        print(error_msg)
        print(f"Error processing document: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/ask")
async def ask_question(request: QuestionRequest):
    """Ask a question about uploaded documents."""
    query = request.question
    if INDEX is None:
        return JSONResponse({"error": "No documents uploaded yet."}, status_code=400)

    try:
        print(f"Received query: {query}")
        retrieved = retrieve_relevant_chunks(query, MODEL, INDEX, DOCS, top_k=3)
        answer = ask_gemini(query, retrieved)
        return JSONResponse({
            "query": query,
            "answer": answer,
            "context_snippets": retrieved
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/")
def root():
    return {"message": "Welcome to the Document RAG API. Use /upload and /ask endpoints."}
