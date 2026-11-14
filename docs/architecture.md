# Architecture notes

## What I was trying to solve

I wanted a question-answering service that can explain where each fact came from. The user should not have to trust a model's confidence. If a field is missing, the system should say it is missing.

## Data flow

1. **Read:** `ingest.py` checks that the uploaded CSV headers match the expected schema. It reads each row as text.
2. **Join:** All four files share the `job_id` field. I keep one record per job, with groups for `skills`, `industries`, `benefits` and `salaries`.
3. **Store:** The data goes into a SQLite `jobs` table. Each original value has a source filename and CSV record number. A second SQLite FTS5 table holds the searchable text.
4. **Retrieve:** If the question includes a numeric job ID, I use an exact primary-key lookup. Otherwise I use tokenized FTS5 search ranked by BM25.
5. **Check intent:** If the question asks for a field that is not present, the guarded system abstains. A missing job ID is not replaced with a different ID.
6. **Answer:** The default route renders source records with a fixed template. In Ollama mode, the model proposes a JSON list of claims. Only exact allowed field/value pairs are accepted, and their citations are restored from the SQLite record, not from model output.
7. **Measure:** The evaluator builds questions from the actual SQLite data, records supported and unsupported claims, and writes CSV/JSON/Markdown reports.

## Why FTS5 rather than embeddings?

At this stage the data is almost entirely short structured fields. Embeddings can be useful for a paragraph such as a full job description, but the source files do not include those descriptions. I kept the system simple and chose retrieval that makes exact ID matching reliable. It also runs fully offline.

This is **lexical RAG** rather than semantic RAG. It does not understand synonyms reliably, and it is not a full relational analytics engine. For example, searching for `IT` or `Medical insurance` can find matching records, but the query `How many IT jobs offer benefits?` is not answered by an accurate SQL aggregate. A proper analytics route or text-to-SQL component would need separate design and testing.

## Baseline versus guardrails

The baseline is **intentionally flawed**. When a requested job is not found, it uses a different job record rather than abstaining. It also returns general job facts for questions about unsupported fields, even when those facts are irrelevant.

The guarded version never uses that fallback. It checks the requested field and ID. The observed reduction in structured errors is caused by those rules, **not** by claiming a new language model is hallucination-free.

## The threat model

- **Cross-job contamination:** a source fact gets attached to a different `job_id`. The exact-key match stops this in guarded mode.
- **Unsupported field:** a question asks for company or title when neither is recorded. Intent checks trigger abstention.
- **False precision:** salary values get converted or interpreted without exchange rates or assumptions. The system leaves them untouched.
- **Unverified benefit:** inferred flags get lost. The system displays the original `inferred` value.
- **LLM invents field/value pairs:** the model output is checked against an exact whitelist of source facts.
- **Made-up citation:** accepted claims receive their citation from the database, not from the model.
- **Malicious search input:** parameterized SQLite queries and quoted FTS terms reduce query injection risk.

The implementation is a demo, not a complete security boundary. It needs auth, rate limits, better auditing and privacy review before production use.

## Production changes I would make

- Use the stored source SHA-256 hashes for data version checks, add a stable version/hash to each citation, and provide a data-refresh strategy.
- Give clients their own data access controls and audit logs.
- Build a real retrieval benchmark with human judgments and measure `recall@k` for non-ID questions.
- Evaluate vector search and hybrid retrieval if job descriptions or natural-language documents are added.
- Move from a local database to managed storage when data volume and concurrent writes justify it.
- Measure actual LLM claims using labeled evidence, not only exact-match structured fields.
- Add runtime tracing, errors, latency percentiles, cost tracking and user feedback.
- Review behavior with the customer because a safe refusal may be better than a confident bad answer.
