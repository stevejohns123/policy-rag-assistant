import streamlit as st
import chromadb
import ollama

col = chromadb.PersistentClient(path="db").get_collection("policies")

st.title("Cybersecurity Policy Assistant")
q = st.text_input("Ask a question")

if q:
    res = col.query(query_texts=[q], n_results=10)
    docs = res["documents"][0]
    metas = res["metadatas"][0]

    context = "\n\n".join(
        f"[{m['source']} p.{m['page']}]\n{d}" for d, m in zip(docs, metas)
    )

    resp = ollama.chat(
        model="llama3.2",
        messages=[
            {
                "role": "system",
                "content": (
                    "Answer using the provided context. Synthesize a direct answer in your own words. "
                    "Every sentence must end with a citation like [file p.X]. "
                    "Only use file and page numbers that appear in the context. "
                    "If the context does not mention the answer, say exactly: "
                    "'The provided documents do not contain this information.'"
                ),
            },
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {q}"},
        ],
    )

    st.write(resp["message"]["content"])
    st.subheader("Sources")
    for d, m in zip(docs, metas):
        with st.expander(f"{m['source']} p.{m['page']}"):
            st.write(d)