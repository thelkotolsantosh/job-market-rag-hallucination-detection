"""Reproducible offline evaluation using claims checked against the source CSV database."""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import time
from pathlib import Path

from .rag import answer, evidence_claims, classify
from .store import connect, find_job, stats


def select_ids(con: sqlite3.Connection, condition: str, n: int) -> list[str]:
    """Use facts derived from source data; never hard-code expected job attributes."""
    if condition == "salaries":
        predicate = "facts_json LIKE '%\"salary_id\"%'"
    elif condition == "benefits":
        predicate = "facts_json LIKE '%\"inferred\"%'"
    else:
        predicate = "1=1"
    rows = con.execute(f"SELECT job_id FROM jobs WHERE {predicate} ORDER BY job_id LIMIT ?", (n * 6,)).fetchall()
    if condition in {"skills", "industries", "no_salary"}:
        field = {"skills": "skills", "industries": "industries", "no_salary": "salaries"}[condition]
        records = [(r["job_id"], find_job(con, r["job_id"])) for r in rows]
        return [job_id for job_id, doc in records if (not doc["facts"][field] if condition == "no_salary" else bool(doc["facts"][field]))][:n]
    return [r["job_id"] for r in rows][:n]


def make_benchmark(con: sqlite3.Connection, n: int = 10) -> list[dict]:
    """Eight test categories, including deliberately unanswerable prompts."""
    cases = []
    kinds = [
        ("skills", "skills", "Which skill codes are listed for job {id}?"),
        ("industries", "industries", "Which industry IDs are listed for job {id}?"),
        ("benefits", "benefits", "What benefits are listed for job {id}?"),
        ("salaries", "salaries", "What salary is listed for job {id}?"),
        ("no_salary", "no_salary", "What salary is listed for job {id}?"),
        ("company_missing", "skills", "What company posted job {id}?"),
        ("meaning_missing", "industries", "What does the industry code mean for job {id}?"),
    ]
    for kind, selector, template in kinds:
        for job_id in select_ids(con, selector, n):
            cases.append({"case": kind, "job_id": job_id, "question": template.format(id=job_id)})
    existing = {r["job_id"] for r in con.execute("SELECT job_id FROM jobs WHERE job_id LIKE '99999999%' LIMIT 200")}
    generated = 0
    start = 999999999990000
    while generated < n:
        job_id = str(start + generated)
        if job_id not in existing:
            cases.append({"case": "nonexistent_job", "job_id": job_id, "question": f"What skill codes are listed for job {job_id}?"})
        generated += 1
    return cases


def _claim_key(claim: dict) -> tuple:
    return (claim["field"], claim["value"], claim.get("inferred"))


def score(con: sqlite3.Connection, cases: list[dict], mode: str) -> tuple[dict, list[dict]]:
    totals = {"questions": 0, "answered": 0, "abstained": 0, "answers_with_unsupported_claims": 0,
              "answers_with_irrelevant_claims": 0, "unsupported_claims": 0, "total_claims": 0,
              "expected_answerable": 0, "correct_abstentions": 0, "unjustified_answers": 0,
              "false_abstentions": 0, "gold_claims": 0, "recalled_gold_claims": 0,
              "model_rejected_claims": 0}
    details = []
    started = time.perf_counter()
    for case in cases:
        job = find_job(con, case["job_id"])
        intent = classify(case["question"])
        gold = evidence_claims(job, intent) if job and intent != "unknown_field" else []
        valid = {_claim_key(claim) for claim in gold}
        source_truth = {_claim_key(claim) for claim in evidence_claims(job, "summary")} if job else set()
        expected_answerable = bool(gold)
        response = answer(con, case["question"], mode=mode)
        claims = response["claims"]
        # A claim is supported if its values match the actual requested job (not an unrelated retrieved job).
        unsupported = [x for x in claims if _claim_key(x) not in source_truth]
        irrelevant = bool(claims and intent == "unknown_field")
        actual_keys = {_claim_key(x) for x in claims}
        totals["questions"] += 1
        totals["answered"] += int(response["status"] == "answered")
        totals["abstained"] += int(response["status"] == "abstained")
        totals["answers_with_unsupported_claims"] += int(bool(unsupported))
        totals["answers_with_irrelevant_claims"] += int(irrelevant)
        totals["unsupported_claims"] += len(unsupported)
        totals["total_claims"] += len(claims)
        totals["expected_answerable"] += int(expected_answerable)
        totals["correct_abstentions"] += int(not expected_answerable and response["status"] == "abstained")
        totals["unjustified_answers"] += int(not expected_answerable and response["status"] == "answered")
        totals["false_abstentions"] += int(expected_answerable and response["status"] == "abstained")
        totals["gold_claims"] += len(valid)
        totals["recalled_gold_claims"] += len(valid & actual_keys)
        totals["model_rejected_claims"] += len(response["rejected_model_claims"])
        details.append({"case": case["case"], "job_id": case["job_id"], "question": case["question"],
                        "expected_answerable": expected_answerable, "status": response["status"],
                        "matched_job_id": response["matched_job_id"], "unsupported_claim_count": len(unsupported),
                        "irrelevant_claims": irrelevant, "claim_count": len(claims),
                        "rejected_model_claims": len(response["rejected_model_claims"]),
                        "answer": response["answer"], "citations": ";".join(response["citations"]),
                        "proposed_but_rejected": json.dumps(response["rejected_model_claims"])})
    q = totals["questions"]
    answered = totals["answered"]
    metrics = {
        "mode": mode, "counts": totals,
        "rates_pct": {
            "answer_hallucination_rate_all_questions": percentage(totals["answers_with_unsupported_claims"], q),
            "answer_hallucination_rate_answered_only": percentage(totals["answers_with_unsupported_claims"], answered),
            "unsupported_claim_rate": percentage(totals["unsupported_claims"], totals["total_claims"]),
            "unjustified_answer_rate_all_questions": percentage(totals["unjustified_answers"], q),
            "abstention_rate": percentage(totals["abstained"], q),
            "correct_abstention_rate_on_unanswerable": percentage(totals["correct_abstentions"], q - totals["expected_answerable"]),
            "gold_claim_recall": percentage(totals["recalled_gold_claims"], totals["gold_claims"]),
        },
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "definition": "Structured claims checked against exact values in the requested job's CSV records. Not a full natural-language hallucination detector.",
    }
    return metrics, details


def percentage(numerator: int, denominator: int) -> float | None:
    return round(100 * numerator / denominator, 2) if denominator else None


def write_outputs(out: Path, report: dict, cases: list[dict], rows: list[dict]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (out / "benchmark_questions.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["case", "job_id", "question"])
        writer.writeheader(); writer.writerows(cases)
    with (out / "benchmark_results.csv").open("w", newline="", encoding="utf-8") as file:
        if rows:
            writer = csv.DictWriter(file, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    lines = ["# Evaluation results", "", "Generated from the local source CSVs. No numbers were invented.", "",
             "**Important:** The baseline is intentionally unsafe retrieval, **not** an LLM. These numbers measure structured unsupported claims, not every possible free-text hallucination.", "",
             "| Metric | " + " | ".join(report["modes"]) + " |",
             "|---|" + "---:|" * len(report["modes"])]
    for metric in ["answer_hallucination_rate_all_questions", "answer_hallucination_rate_answered_only", "unsupported_claim_rate", "unjustified_answer_rate_all_questions", "abstention_rate", "correct_abstention_rate_on_unanswerable", "gold_claim_recall"]:
        vals = [report["modes"][mode]["rates_pct"][metric] for mode in report["modes"]]
        lines.append("| " + metric.replace("_", " ") + " | " + " | ".join("N/A" if v is None else f"{v:.2f}%" for v in vals) + " |")
    lines += ["", "## What the numbers mean", "", "- **Answer hallucination rate (all questions):** prompts with one or more unsupported structured claims divided by all prompts.",
              "- **Unsupported claim rate:** structured claims absent from the requested job's source records divided by all returned claims (regardless of question wording).",
              "- **Unjustified answer rate:** answered prompts whose requested information is unavailable; can include irrelevant but otherwise true claims.",
              "- **Gold claim recall:** fraction of all expected factual claims correctly returned; useful because abstaining on everything would otherwise look safe.",
              "- **Correct abstention:** unanswered cases where the required information is not in the dataset.",
              "- **Irrelevant claims:** source-backed claims that do not answer the asked question, counted separately from factual hallucinations.",
              "", "## Limits", "", "The evaluation checks exact recorded field/value pairs and the job ID. It does not check open-ended prose or semantic paraphrases.",
              "It does not claim that a language model has zero hallucinations. To assess prose, manually review and label model responses (see docs/evaluation.md).", ""]
    (out / "metrics.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate baseline vs guarded (and optionally Ollama) against CSV truth")
    parser.add_argument("--db", type=Path, default=Path("data/processed/jobs.sqlite"))
    parser.add_argument("--out", type=Path, default=Path("reports"))
    parser.add_argument("--n-per-case", type=int, default=10, help="10 -> up to 80 questions")
    parser.add_argument("--limit", type=int, default=0, help="optional cap on benchmark size; 0 means no cap")
    parser.add_argument("--mode", choices=["compare", "baseline", "guarded", "ollama"], default="compare")
    args = parser.parse_args()
    with connect(args.db) as con:
        benchmark = make_benchmark(con, max(args.n_per_case, 1))
        if args.limit:
            benchmark = benchmark[:args.limit]
        modes = ("baseline", "guarded") if args.mode == "compare" else (args.mode,)
        result, all_rows = {}, []
        for mode in modes:
            result[mode], rows = score(con, benchmark, mode)
            all_rows.extend({"mode": mode, **row} for row in rows)
        report = {"dataset": stats(con), "benchmark_size": len(benchmark), "modes": result}
    write_outputs(args.out, report, benchmark, all_rows)
    print(json.dumps({"benchmark_size": len(benchmark), "rates_pct": {k: v["rates_pct"] for k, v in result.items()}}, indent=2))
    print("Saved", args.out / "metrics.md")


if __name__ == "__main__":
    main()
