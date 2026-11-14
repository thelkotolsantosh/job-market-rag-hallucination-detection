# Evaluation results

Generated from the local source CSVs. No numbers were invented.

**Important:** The baseline is intentionally unsafe retrieval, **not** an LLM. These numbers measure structured unsupported claims, not every possible free-text hallucination.

| Metric | baseline | guarded |
|---|---:|---:|
| answer hallucination rate all questions | 12.50% | 0.00% |
| answer hallucination rate answered only | 14.29% | 0.00% |
| unsupported claim rate | 6.17% | 0.00% |
| unjustified answer rate all questions | 37.50% | 0.00% |
| abstention rate | 12.50% | 50.00% |
| correct abstention rate on unanswerable | 25.00% | 100.00% |
| gold claim recall | 100.00% | 100.00% |

## What the numbers mean

- **Answer hallucination rate (all questions):** prompts with one or more unsupported structured claims divided by all prompts.
- **Unsupported claim rate:** structured claims absent from the requested job's source records divided by all returned claims (regardless of question wording).
- **Unjustified answer rate:** answered prompts whose requested information is unavailable; can include irrelevant but otherwise true claims.
- **Gold claim recall:** fraction of all expected factual claims correctly returned; useful because abstaining on everything would otherwise look safe.
- **Correct abstention:** unanswered cases where the required information is not in the dataset.
- **Irrelevant claims:** source-backed claims that do not answer the asked question, counted separately from factual hallucinations.

## Limits

The evaluation checks exact recorded field/value pairs and the job ID. It does not check open-ended prose or semantic paraphrases.
It does not claim that a language model has zero hallucinations. To assess prose, manually review and label model responses (see docs/evaluation.md).
