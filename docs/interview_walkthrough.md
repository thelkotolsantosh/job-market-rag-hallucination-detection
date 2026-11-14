# Interview walkthrough — about 3 minutes

## How I would introduce it

> "I built a small RAG system using four CSV files about job skills, industries, benefits and salaries. I wanted to solve two problems: finding the correct source record, and preventing an answer from claiming facts that aren't in the source. I also added an evaluation script so I can measure the difference rather than rely on a demo that just looks convincing."

## My demo order

**1. Show the data and interface.** Open `http://127.0.0.1:8000` and point out the dataset counts. Explain that the records have IDs and codes, not full descriptions.

**2. Ask an answerable question.** Use `What skills are listed for job 3884428798?`. Expand the structured result and show `job_skills.csv:<row>` citations. Explain why a source-row reference is better than an unverified citation string created by an LLM.

**3. Ask an impossible question.** Use `What company posted job 3884428798?`. The guarded pipeline refuses to invent a company name because the CSVs contain none.

**4. Show the dangerous failure.** Ask `What skills are listed for job 999999999990000?` with baseline mode. The baseline substitutes a different job and wrongly associates those skills with the requested ID. Switch back to guarded and show the refusal.

**5. Open the benchmark.** Show `reports/metrics.md`: 80 questions, unsupported facts in 12.5% of questions before the check and 0% after. Explain that this is an **intentionally weak retrieval baseline**, not an LLM hallucination benchmark. Also show the separate correct-abstention and claim-recall metrics.

**6. Explain the system choices.** Show `src/job_rag/ingest.py`, `rag.py`, `ollama_client.py`, `evaluate.py` and `tests/test_pipeline.py`. Say why SQLite and exact matching fit IDs and codes, and why you would test semantic search if the client brought real job descriptions.

## Questions I should be ready for

- **How would you measure LLM hallucinations?** I would have humans verify atomic claims against source evidence. The repo has a labeling template and a calculator for the resulting rates.
- **Why is abstention important?** Because a wrong company or salary can hurt a user more than a clear "not in the supplied data."
- **Does 0% mean safe?** No. It means the constrained structured output contained no unsupported pairs in these 80 questions.
- **Why not use a vector database?** The current data is mostly short IDs and codes. I would test hybrid retrieval only after I know the customer's queries and data.
- **How would you deploy this to a client?** Start by checking data ownership, authentication, customer requirements, privacy, logging and quality thresholds. Then run a pilot with reviewed cases before scaling.

## Resume bullet — use only if accurate for your own work

"Built a CSV-backed RAG prototype with FastAPI, SQLite FTS5 and source-row citations; added deterministic claim validation and an 80-question benchmark to measure unsupported answers, correct abstentions and answer coverage."

If asked what you personally built, explain which parts you implemented, tested or modified yourself. Do not present tools you have not run as tested results.
