"""Calculate true free-text claim labels after a human has reviewed atomic claims."""
from __future__ import annotations
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from .evaluate import percentage


def score_manual(path: Path) -> dict:
    groups = defaultdict(lambda: defaultdict(list))
    incomplete = 0
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"answer_id", "model", "atomic_claim", "supported", "source_ref"}
        if not reader.fieldnames or not required <= set(reader.fieldnames):
            raise ValueError(f"Expected columns: {sorted(required)}")
        for row_number, row in enumerate(reader, 2):
            if not row["atomic_claim"].strip() or not row["supported"].strip():
                incomplete += 1
                continue
            status = row["supported"].strip().lower()
            if status not in {"yes", "no", "uncertain"}:
                raise ValueError(f"Row {row_number}: supported must be yes, no, uncertain, or blank")
            if status == "yes" and not row["source_ref"].strip():
                raise ValueError(f"Row {row_number}: a supported claim needs a source_ref")
            if status == "uncertain":
                incomplete += 1
                continue
            groups[row["model"]][row["answer_id"]].append(status)
    result = {}
    for model, answers in groups.items():
        total_claims = sum(map(len, answers.values()))
        bad_claims = sum(status == "no" for group in answers.values() for status in group)
        bad_answers = sum("no" in group for group in answers.values())
        result[model] = {"labeled_answers": len(answers), "labeled_claims": total_claims,
                         "unsupported_claims": bad_claims, "answers_with_unsupported_claims": bad_answers,
                         "unsupported_claim_rate_pct": percentage(bad_claims, total_claims),
                         "answer_hallucination_rate_pct": percentage(bad_answers, len(answers))}
    return {"models": result, "unlabeled_or_uncertain_rows": incomplete,
            "note": "These are manual labels. Split each answer into factual atomic claims; inspect provided citations; label each yes/no/uncertain. A partially labeled answer can underestimate its error rate."}


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute manually labeled free-text hallucination rate")
    parser.add_argument("--annotations", type=Path, default=Path("docs/manual_annotations_template.csv"))
    args = parser.parse_args()
    print(json.dumps(score_manual(args.annotations), indent=2))


if __name__ == "__main__":
    main()
