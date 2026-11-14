# How I measured hallucinations

## What is being measured?

The default pipeline produces **structured claims**, such as:

```json
{"field": "skill_abr", "value": "IT", "source": {"file": "job_skills.csv", "row": 2}}
```

The evaluation does not rely on an LLM as a judge. It loads the actual record for the *requested* job ID and checks whether the claim's field/value pair exists there. For benefits, the `inferred` flag is also compared. It does not use the job the retriever happened to return as the truth source.

This is a narrow but reproducible definition of unsupported factual claims. It is not the same as evaluating the truth of arbitrary natural-language answers.

## How I created the benchmark

`python -m job_rag.evaluate` reads the SQLite database and generates **80 questions** with 10 examples in each category:

1. Skill codes for existing jobs.
2. Industry IDs for existing jobs.
3. Benefits for existing jobs.
4. Salaries for existing jobs.
5. Salary questions for jobs with no salary row.
6. Company-name questions, which cannot be answered from these files.
7. Industry-code meaning questions, which need a missing lookup table.
8. Questions about job IDs that are not in the files.

The expected claims are produced from the joined CSV records. They are not prefilled guesses.

Run:

```bash
python -m job_rag.evaluate --n-per-case 10
```

Then read:

- `reports/metrics.json` — machine-readable summary and counts.
- `reports/metrics.md` — comparison table.
- `reports/benchmark_questions.csv` — questions.
- `reports/benchmark_results.csv` — per-question outcomes, returned answer and citations.

## Exact formulas

**Answer hallucination rate — all questions**

`100 × (number of questions with >=1 unsupported factual claim) / all test questions`

**Answer hallucination rate — answered questions only**

`100 × (number of answered questions with >=1 unsupported factual claim) / answered questions`

**Unsupported claim rate**

`100 × (number of claims not found in the requested job's source records) / all returned claims`

**Unjustified answer rate**

`100 × (number of answered questions that have no answer in the supplied source fields) / all test questions`

**Correct abstention rate**

`100 × (number of correctly refused unanswerable questions) / number of unanswerable questions`

**Gold claim recall**

`100 × (number of expected claims returned correctly) / number of expected source-backed claims`

An answer about an unsupported company name may include other true job facts. Those are *irrelevant*, but they are not necessarily false. That is why the benchmark keeps the relevance/answerability error separate from the source-factual error.

## Actual measured results

On the four uploaded CSV files:

| Measure | Baseline | Guarded |
|---|---:|---:|
| All questions | 80 | 80 |
| Questions answered | 70 | 40 |
| Questions correctly abstained | 10 | 40 |
| Questions containing unsupported facts | 10 | 0 |
| Unsupported claims | 20 / 324 | 0 / 123 |
| Hallucination rate (all questions) | **12.50%** | **0.00%** |
| Hallucination rate (answered only) | **14.29%** | **0.00%** |
| Unsupported claim rate | **6.17%** | **0.00%** |
| Unjustified answer rate | **37.50%** | **0.00%** |
| Correct abstention rate | **25.00%** | **100.00%** |
| Gold claim recall | **100.00%** | **100.00%** |

**Interpretation:** the unsafe system sometimes uses the first job in the database when it cannot find the requested ID. This produces wrong-job facts. The guarded system refuses this fallback. Both approaches recover the expected claims on answerable questions in this limited benchmark, which is why the recall is 100% for both.

**Do not say:** "My LLM hallucination rate is zero."

**Say:** "On 80 structured test questions, source-unverified claims fell from 12.5% of questions to 0% after adding exact-ID checks and refusal rules. This benchmark tests a deliberately unsafe retrieval baseline, not an LLM's natural-language hallucination rate."

## What about natural-language LLMs?

A model might paraphrase a correct fact, add an unsupported explanation, or make an implication that the strict field/value validator cannot understand. To measure that, I would:

1. Create a reviewed set of user questions and correct evidence.
2. Run **the same questions** against each prompt/model/retriever variant.
3. Split each answer into atomic factual claims. "The company is X and the salary is Y" is two claims.
4. Label each claim **yes** (supported), **no** (unsupported), or **uncertain** after checking the original evidence.
5. Compute claim and answer hallucination rates with `evaluate_manual.py`.
6. Report uncertainty, sample size, abstention and coverage alongside hallucination rate. Review some answers with a second annotator.

The file `docs/manual_annotations_template.csv` is a starting template. Its labels are intentionally blank. They are **not real measurements**. Run:

```bash
python -m job_rag.evaluate_manual --annotations docs/manual_annotations_template.csv
```

The script ignores blank/uncertain rows but reports how many it skipped. Do not publish a result based on a partially labeled answer set as though it were complete.

## Optional Ollama comparison

The `ollama` mode asks a local model to propose source-backed JSON claims. The validator rejects unsupported proposed pairs and restores source citations on accepted pairs. Run a small test:

```bash
python -m job_rag.evaluate --mode ollama --n-per-case 2 --out reports/ollama
```

The output tells you how many model-proposed claims were rejected and how many final accepted claims were supported. A zero rate **after validation** does not imply the raw model had a zero error rate; inspect `proposed_but_rejected` in `benchmark_results.csv` as well.

No Ollama measurements are included in the committed baseline report because a local model was not run for this build.

## Known limits of this evaluation

- Eight simple templates are not a representative customer workload.
- The baseline is deliberately bad and should not be compared to a production competitor.
- The model and retriever are not tested against natural-language synonyms or long documents.
- The guarded result can score zero unsupported claims because it only emits exact source values; that says nothing about open-ended prose safety.
- The benchmark is built from the same schema as the pipeline, so independent customer-labeled cases are important before deployment.
- Exact-match validation can reject a correct paraphrase. This is an expected precision/coverage trade-off.
