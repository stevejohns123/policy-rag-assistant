# Cybersecurity Policy RAG Assistant

A local, free retrieval-augmented assistant that answers cybersecurity questions from NIST documents and shows the source pages it used. Built to learn how grounded AI works: chunking, embeddings, retrieval, cited generation, and evaluation.

## Stack

- Python, Streamlit (UI)
- ChromaDB with its built-in local embedding model (all-MiniLM-L6-v2)
- pypdf (PDF text extraction)
- Ollama running llama3.2 (3B), no API key or cost

## How it works

```
Question -> embed -> ChromaDB top-k chunks -> prompt with context -> llama3.2 -> answer + [file p.X] citations
```

1. `ingest.py` reads PDFs from `docs/`, splits pages into 1,000-character chunks with 200 overlap, and stores them with source and page metadata (266 chunks).
2. `app.py` retrieves the top chunks for a question, passes them to the model, and displays the answer with a Sources panel.

## Documents used

- NIST CSWP 29 (Cybersecurity Framework 2.0)
- NIST SP 800-61 Rev. 3 (Incident Response)

PDFs are not included. Download them from nist.gov and place them in `docs/`.

## Run it

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
ollama pull llama3.2
python ingest.py
streamlit run app.py
```

## Evaluation

`eval.csv` logs each test question with three checks:

- **Retrieval:** did the expected source file appear in the retrieved chunks?
- **Answer:** does the answer match the source text?
- **Citation:** does every cited `[file p.X]` point to a page that was actually retrieved?

Includes one trap question (a cookie recipe) to test hallucination.

### Results

**V1.3 (one automated run, hand-scored answers, 15 questions plus 1 trap):** 93% top-3 retrieval (14/15), 80% valid citations (12/15), 80% answer accuracy (12/15). The trap question was refused correctly.

| Version | Change | Result |
|---|---|---|
| V1.0 | Basic prompt, 5 chunks | Answer missed facts present in retrieved text (generation failure) |
| V1.1 | 8 chunks, synthesis prompt | Fixed the six-functions miss, but some answers had no citations |
| V1.2 | Prompt requires a citation on every sentence and an exact refusal line | Retrieval 14/15 (93%), citation 11/14 (79%), trap question refused correctly |
| V1.3 | 10 chunks | Fixed 3 of 4 previously failing questions, no regressions on those four |

### Failure types found

- **Retrieval:** a CSF question pulled mostly incident-response chunks until the chunk count increased.
- **Citation:** page ranges that included pages never retrieved; a literal `[file p.X]` placeholder; malformed citations.
- **Generation:** a false refusal on a question the sources may answer; an answer that drifted off topic.

## Limitations

- 16 questions, scored by hand, so treat the percentages as indicative only.
- V1.3 numbers come from one full automated run of all 16 questions.
- A 3B model is inconsistent between runs of the same question.

## Roadmap

1. Add retrieval and citation scoring for answer text (LLM-as-judge)
2. Try a larger model and a reranker
3. Move to AWS Bedrock
4. Add AI security testing and NIST AI RMF governance mapping
