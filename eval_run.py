import csv, re, sys, time
import chromadb, ollama

BACKEND = sys.argv[1] if len(sys.argv) > 1 else "ollama"
GEMINI_MODEL = "gemini-3.1-flash-lite"

if BACKEND == "gemini":
    from google import genai
    from google.genai import types
    gclient = genai.Client()  # reads GEMINI_API_KEY

col = chromadb.PersistentClient(path="db").get_collection("policies")

SYSTEM = (
    "Answer using the provided context. Synthesize a direct answer in your own words. "
    "Every sentence must end with a citation like [file p.X]. "
    "Only use file and page numbers that appear in the context. "
    "If the context does not mention the answer, say exactly: "
    "'The provided documents do not contain this information.'"
)

def ask(user):
    if BACKEND == "ollama":
        return ollama.chat(
            model="llama3.2",
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": user}],
        )["message"]["content"]
    for _ in range(8):
        try:
            r = gclient.models.generate_content(
                model=GEMINI_MODEL,
                contents=user,
                config=types.GenerateContentConfig(system_instruction=SYSTEM),
            )
            return r.text or ""
        except Exception as e:
            print("retrying:", str(e)[:120])
            time.sleep(30)
    return ""

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
    answer = ask(f"Context:\n{context}\n\nQuestion: {q}")

    cites = re.findall(r"([\w.\-]+\.pdf) p\.(\d+)", answer)
    refused = "do not contain" in answer.lower()
    retrieval = "n/a" if expected == "NONE" else ("Y" if expected in top3 else "N")
    if refused:
        citation = "n/a"
    elif not cites:
        citation = "none"
    else:
        citation = "Y" if all((fl, int(p)) in retrieved for fl, p in cites) else "N"

    rows.append({
        "question": q, "expected_source": expected,
        "retrieval_top3": retrieval, "citation_valid": citation,
        "refused": "Y" if refused else "N",
        "answer_correct": "", "answer": answer.replace("\n", " "),
    })
    print(q[:60], "|", retrieval, "|", citation, "|", "refused" if refused else "")
    if BACKEND == "gemini":
        time.sleep(5)

out = f"results_{BACKEND}.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)

scored = [r for r in rows if r["retrieval_top3"] != "n/a"]
cited = [r for r in rows if r["citation_valid"] in ("Y", "N")]
print("\nBackend:", BACKEND)
print("Retrieval top-3:", sum(r["retrieval_top3"] == "Y" for r in scored), "/", len(scored))
print("Citations valid:", sum(r["citation_valid"] == "Y" for r in cited), "/", len(cited))
print("No citations:", sum(r["citation_valid"] == "none" for r in rows))