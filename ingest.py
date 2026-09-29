import os
from pypdf import PdfReader
import chromadb

client = chromadb.PersistentClient(path="db")
col = client.get_or_create_collection("policies")

def chunk(text, size=1000, overlap=200):
    return [text[i:i+size] for i in range(0, len(text), size - overlap)]

for fname in os.listdir("docs"):
    if not fname.endswith(".pdf"):
        continue
    reader = PdfReader(f"docs/{fname}")
    for p, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        for i, c in enumerate(chunk(text)):
            if c.strip():
                col.add(
                    ids=[f"{fname}-{p}-{i}"],
                    documents=[c],
                    metadatas=[{"source": fname, "page": p + 1}],
                )
print("Done:", col.count(), "chunks")