# CareWeave: implementing the HiDevs seven-step workflow

This is a focused adult type 2 diabetes research prototype using synthetic patients. Data, software and retrieval tests do not establish clinical efficacy. Provider credentials are never required to inspect evidence or execute safety rules.

## 1. Data sources and extraction

`data/evidence.json` stores original short summaries referencing NICE NG28, KDIGO 2024 and CPIC 2022. Each includes source ID, publisher, title, section, URL, retrieval date, scope and prototype-review status. These are curated summaries, not a scraped collection of full guidelines or a live literature review.

`scripts/export-corpus.mjs` exports the shared JavaScript corpus and synthetic cases for Python. CI checks that they do not drift:

```sh
node scripts/export-corpus.mjs --check
```

For an explicitly supplied local public PDF, Markdown or UTF-8 text file, use the appropriate extractor:

```sh
python -m rag.ingest /path/to/public-guideline.pdf --source-id LOCAL-GUIDE --source-url https://publisher.example/guideline --output review-draft.json
```

PyPDF handles PDFs; native text reading handles Markdown/text. PDF pages remain numbered. Scanned PDFs need OCR outside this implementation. Extraction produces an **unreviewed draft**, not an indexed clinical source. Check text quality, provenance, licensing and section boundaries; convert relevant sections to approved JSON records before indexing. Unknown or unreviewed records are rejected. No uncontrolled crawlers or uploaded patient documents are supported.

## 2. Preprocessing

`rag/ingestion.py` normalizes Unicode, removes NUL characters, collapses repeated whitespace and retains paragraph separation. It validates provenance, removes identical repeated records, rejects conflicting source IDs and adds SHA-256 content hashes. Distinct sources are retained even when they corroborate the same clinical point.

## 3. Splitting and chunking

The MiniLM tokenizer provides offsets into the original text. Each document chunk contains at most 180 content tokens with 30-token overlap. Source title, section and URL remain in metadata. Token offsets and content hashes make chunks inspectable. Long patient queries are also embedded in bounded windows, then averaged and re-normalized, avoiding silent query truncation. Existing short summaries often fit in a single chunk; synthetic long-text tests exercise actual document overlap.

## 4. Embeddings and knowledge base

`rag/retrieval.py` loads `sentence-transformers/all-MiniLM-L6-v2` locally on CPU with remote-code execution disabled, normalizes document/query embeddings, and queries a persistent Chroma cosine index. The tested model revision is pinned in code. Cached snapshots are loaded offline to avoid repeated remote metadata/template checks; the first download still needs network access. An index fingerprint covers corpus chunks, model identity, pinned revision and schema version, preventing reuse across changed corpora. Only public evidence embeddings are persisted. Query vectors and profiles are not written to the vector store.

Chroma is the first choice. An initialization failure can use FAISS only if its optional dependency is installed; the report shows the fallback reason. FAISS uses normalized inner product, equivalent to cosine for these unit-length vectors. There is no fabricated neural fallback to TF-IDF. The separate JavaScript demo intentionally retains its lightweight sparse retrieval implementation.

Official references: [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), [Chroma PersistentClient](https://docs.trychroma.com/reference/python/client).

## 5. Query processing and AI engine

`rag/pipeline.py` first calls the existing safety core via JSON stdin, without a shell. Withheld cases do not trigger embedding or model calls. Supported profiles become a retrieval query. Semantic matches are combined with all evidence IDs required by the safety rules, so ranking cannot discard a safety citation.

Groq/Llama receives a bounded context of the profile, options, risks, missing information and selected evidence. The prompt treats profile fields and evidence as untrusted data, prohibits additional medicines/doses/references, and asks for a concise rationale, uncertainty and existing evidence IDs. JSON mode is followed by local validation of exact fields, size bounds and citation IDs. Provider failures preserve the independent report. Citation validation does not prove every generated claim is entailed; human review remains essential.

Model access may vary by account. The configured default is `llama-3.3-70b-versatile`, adjustable through `GROQ_MODEL`. No free-service guarantee is made. See [Groq JSON mode](https://console.groq.com/docs/structured-outputs) and [available models](https://console.groq.com/docs/models).

Optional `rag/history.py` writes synthetic reports to MongoDB only after explicit opt-in. Random session IDs separate this prototype's history; a TTL index requests removal after seven days, though cleanup is asynchronous. No real patient records or authenticated multi-user medical storage are supported. History is not fed back to the LLM.

## 6. UI and deployment

Run `streamlit_app.py` with Python 3.12 and Node.js available. It exposes patient inputs, safety signals, semantic chunks, provenance, rationale, follow-up, optional provider synthesis, JSON download and optional synthetic history. Input/configuration changes invalidate old reports. Runtime credentials come from server-side environment variables or a local ignored `.env` file.

The repository contains two explicit runtime tracks:

| Track | Runtime | Retrieval | Hosting |
| --- | --- | --- | --- |
| Lightweight web | Node / Worker | TF-IDF cosine | Existing owner-private Sites deployment |
| HiDevs semantic | Python + Node safety core | MiniLM + Chroma / FAISS | Local Streamlit; deploy separately on a Python host |

For Streamlit hosting, point the service at `streamlit_app.py`, install `requirements.txt`, supply Node.js (`packages.txt` for Community Cloud), configure secrets server-side, and provide model-download network access and sufficient memory. Optional FAISS deployments also need `requirements-faiss.txt`. This repository does not claim that a Streamlit deployment or judge-accessible public endpoint has been completed.

## 7. Testing and optimization

```sh
npm test
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/evaluate_rag.py --output docs/semantic-evaluation.json
```

The semantic benchmark runs the actual encoder and vector backend over five developer-authored retrieval questions. It records backend, corpus fingerprint, model revision, setup latency, per-query latency and hit@3. This small check is neither a held-out benchmark nor a clinical evaluation. Groq generation quality and live MongoDB persistence require credentials and are not substituted with invented scores.

Public document embeddings are cached; models/indexes are cached across Streamlit reruns. Patient context and query vectors are not shared in that cache. CI runs software and Streamlit safety checks without downloading the embedding model; the real retrieval benchmark is a separate explicit command. Future expansion needs a larger reviewed corpus, held-out relevance labels, clinician review and generation entailment evaluation before claims of performance or safety.
