from langchain.text_splitter import RecursiveCharacterTextSplitter
from llama_index.core import Document


def recursive_chunk_pdf(content_item: dict,
                        chunk_size: int = 1000,
                        chunk_overlap: int = 150):
    """
    Recursively chunk PDF text using RecursiveCharacterTextSplitter.

    Args:
        content_item (str): COntent Item obj.
        chunk_size (int): Target chunk size (in characters).
        chunk_overlap (int): Number of overlapping characters between chunks.

    Returns:
        List[Document]: List of LlamaIndex Document chunks ready for indexing.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    text = content_item['text']
    file_name = content_item['metadata']['source']

    chunks = splitter.split_text(text)    
    docs = [Document(text=chunk, metadata={"source": file_name}) for chunk in chunks]

    return docs
