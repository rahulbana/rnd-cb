from llama_index.readers.docling import DoclingReader

reader = DoclingReader()
# docs = reader.load_data(file_path="https://arxiv.org/pdf/2408.09869")
# print(f"{docs[0].text[389:442]}...")


docs = reader.load_data(file_path="./B2026323_01-SEP-2025.pdf")
print(f"{docs[0]}")