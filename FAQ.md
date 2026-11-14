# FAQ — 20 Technical Interview Questions

I wrote these answers to explain the decisions in this repository in plain language. They are the answers I would give in a technical interview, including the things I would change if the project had to serve real customers.

### 1. Why did you choose Python 3.11?

Python 3.11 is widely supported and has good performance for a small backend like this. The code does not need brand-new language features. I used 3.11 for the README and Docker image so others can reproduce the setup. The code also ran in a Python 3.13 test environment, but I do not assume every dependency will behave identically on every Python release.

### 2. Why did you choose FastAPI 0.128.2?

FastAPI provides request validation, clear route definitions and automatic API docs. I pinned `0.128.2` to make installs more repeatable. I did not choose it because it is always the newest release. Before a production deployment, I would review security advisories and upgrade the version after running tests.

### 3. Why did you use Uvicorn 0.48.0?

Uvicorn runs the FastAPI app as an ASGI server. Version `0.48.0` is pinned so the demo uses the same tested dependency version. `--reload` is for local development only. In production, I would choose a proper deployment setup with monitoring, worker sizing and timeouts.

### 4. Why did you use pytest 9.0.2?

Pytest makes it easy to check ingestion, retrieval, answer rules, source citations and API endpoints. Version `9.0.2` is the version tested for this project. I use small test CSVs so GitHub Actions can run the tests quickly without loading the full dataset.

### 5. Why did you use httpx 0.28.1?

FastAPI's test client uses HTTP tooling to send requests to the app during tests. I pinned `httpx` to avoid an unexpected dependency change breaking API tests. The main ingestion and retrieval logic does not need httpx.

### 6. Why pin package versions in `requirements.txt`?

A version range may install different packages next month. Exact versions make the demo easier to reproduce. Pinning is not the same as applying security updates, so I would regularly review and update dependencies in a real service.

### 7. Why use SQLite instead of PostgreSQL?

The source data is a few CSV files, and the demo runs on one machine. SQLite needs no separate database server, which makes setup simple for a recruiter. PostgreSQL would be a better option if multiple users were writing data at the same time or if the service needed larger operational features.

### 8. Why use SQLite FTS5 and BM25 rather than FAISS or a vector database?

The columns mostly contain IDs, short codes and benefit names. For these, exact strings and keyword matches are important. FTS5 gives a full-text index and BM25 ranking without having to download embedding models. If I added job descriptions and free-text questions, I would benchmark embeddings or hybrid search against FTS5 rather than assuming they are better.

### 9. Is this a real RAG pipeline if it does not use embeddings?

Yes. RAG means retrieving external information and using it to support answers. Embeddings are one way to retrieve information, not a requirement. The guarded default builds answers deterministically, while Ollama is an optional generation component. I would describe it as **lexical RAG with optional local LLM generation**, not semantic vector RAG.

### 10. Why did you avoid LangChain or another orchestration framework?

The pipeline is short: ingest, retrieve, validate, answer and evaluate. Plain Python makes those steps easy to see and debug. A framework may help once the workflow has many tools, model providers or retrieval stages, but I wanted to understand and test the basic logic first.

### 11. Why join the files using `job_id`?

All four CSVs contain `job_id`. That gives a clear link between salary, benefits, industries and skills. I keep the original IDs as strings so I do not change their values or accidentally lose precision.

### 12. Why store one searchable document per job?

A job is the unit people ask questions about. One document groups the available facts for a single job and reduces the risk of mixing two job IDs. The original field values and source-row references are also stored as structured JSON, so the answer does not depend on parsing the search text.

### 13. Why not convert every salary to yearly USD?

The CSV has different currencies and pay periods. Converting them would require verified exchange rates, dates and assumptions about working hours. A wrong conversion could be worse than leaving the original value. This project shows the exact salary figure, currency and pay period from the source.

### 14. Why keep the benefits `inferred` field?

A benefit marked as inferred should not be presented as a confirmed benefit. The answer includes the flag. This lets someone reading the output make the distinction without checking the CSV themselves.

### 15. What happens if the question asks for a company name or a job title?

The guarded pipeline refuses to answer because those fields are missing. It does not use a model's general knowledge to fill them in. The baseline intentionally handles this badly so I can demonstrate why refusals and field checks matter.

### 16. How do you know that a citation is real?

During CSV ingestion, I save the source filename and CSV record number for each fact. When a claim is displayed, the citation comes from the saved source record. An LLM cannot supply its own accepted citation. The SQLite metadata also stores a SHA-256 hash of each source file. In production I would put a stable dataset version or hash on every citation so older answers remain traceable after a refresh.

### 17. How do you calculate hallucination rate?

For the offline structured benchmark, I compare every returned field/value with the actual records for the **requested** job. I count the fraction of questions with at least one unsupported claim and also count unsupported claims divided by total claims. I report the denominators and number of answers. For a free-text LLM, I would label atomic factual claims by hand or use a calibrated evaluator with regular human checks.

### 18. Is an off-topic answer always a hallucination?

No. A model could give correct facts that do not answer the question. That is a relevance or answerability failure, but not necessarily a false factual claim. This repo reports **unjustified answers** separately from **unsupported facts**. Otherwise the hallucination metric would mix different problems.

### 19. How do you prevent prompt injection and wrong-job answers?

The code treats the CSV values and model responses as untrusted data. It uses parameterized SQL and safe FTS query construction. For an explicit job ID, the guarded mode requires an exact record. The model can only propose allowed field/value pairs; the validator reattaches the actual source citations. This reduces risk, but it is not a complete security review or a guarantee against every kind of injection.

### 20. What would you improve before showing this to a real customer?

First I would ask what questions they need answered and what mistakes would be expensive. Then I would add proper dataset ownership checks, authentication, document versioning, latency and error monitoring, human-reviewed LLM evaluation, a larger test set, access controls and feedback collection. I would compare FTS5, vector search and hybrid search on the customer's real queries. Those choices depend on the customer, which is central to Forward Deployed Engineering.
