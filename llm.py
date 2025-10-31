from dotenv import load_dotenv
load_dotenv()
import os
import google.generativeai as genai

def ask_gemini(query, retrieved_chunks):
    """Combine top retrieved chunks and query Gemini for contextual answer."""
    context = "\n\n".join(retrieved_chunks)
    prompt = f"""
        You are a helpful assistant. Use the following extracted context from a document
        to answer the user's question accurately and concisely.

        Context:
        {context}

        Question:
        {query}

        Answer:"""

    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel("gemini-2.5-flash")

    response = model.generate_content(prompt)
    return response.text.strip()

