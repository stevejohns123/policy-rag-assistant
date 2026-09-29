import csv, re
import chromadb, ollama

col = chromadb.PersistentClient(path="db").get_collection("policies")

SYSTEM = (
    "Answer using the provided context. Synthesize a direct answer in your own words. "
    "Every sentence must end with a citation like [file p.X]. "
    "Only use file and page numbers that appear in the context. "
    "If the context does not mention the answer, say exactly: "
    "'The provided documents do not contain this information.'"
)

seen, questions = set(), []
with open("eval.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["question"] not in seen:
            seen.add(r["question"])
            questions.append((r["question"], r["expected_source"]))

rows = []
for q, expected in questions:
    res = col.query(query_texts=[q], n_results=10)
    metas = res["metadatas"][0]
    docs = res["documents"][0]
    retrieved = {(m["source"], m["page"]) for m in metas}
    top3 = [m["source"] for m in metas[:3]]
    context = "\n\n".join(
        f"[{m['source']} p.{m['page']}]\n{d}" for d, m in zip(docs, metas)
    )
    answer = ollama.chat(
        model="llama3.2",
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {q}"},
        ],
    )["message"]["content"]

    cites = re.findall(r"([\w.\-]+\.pdf) p\.(\d+)", answer)
    refused = "do not contain" in answer.lower()
    if expected == "NONE":
        retrieval = "n/a"
    else:
        retrieval = "Y" if expected in top3 else "N"
    if refused:
        citation = "n/a"
    elif not cites:
        citation = "none"
    else:
        citation = "Y" if all((f, int(p)) in retrieved for f, p in cites) else "N"

    rows.append({
        "question": q, "expected_source": expected,
        "retrieval_top3": retrieval, "citation_valid": citation,
        "refused": "Y" if refused else "N",
        "answer_correct": "", "answer": answer.replace("\n", " "),
    })
    print(q[:60], "|", retrieval, "|", citation, "|", "refused" if refused else "")

with open("results_v1_3.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)

scored = [r for r in rows if r["retrieval_top3"] != "n/a"]
cited = [r for r in rows if r["citation_valid"] in ("Y", "N")]
print("\nRetrieval top-3:", sum(r["retrieval_top3"] == "Y" for r in scored), "/", len(scored))
print("Citations valid:", sum(r["citation_valid"] == "Y" for r in cited), "/", len(cited))
print("No citations:", sum(r["citation_valid"] == "none" for r in rows))