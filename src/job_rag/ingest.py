"""Build an auditable SQLite knowledge base from the four supplied CSVs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

COLUMNS = {
    "job_skills.csv": ["job_id", "skill_abr"],
    "job_industries.csv": ["job_id", "industry_id"],
    "benefits.csv": ["job_id", "inferred", "type"],
    "salaries.csv": ["salary_id", "job_id", "max_salary", "med_salary", "min_salary", "pay_period", "currency", "compensation_type"],
}
CATEGORIES = ("skills", "industries", "benefits", "salaries")


def empty_record() -> dict:
    return {"skills": [], "industries": [], "benefits": [], "salaries": []}


def hash_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_records(data_dir: Path) -> tuple[dict, dict, dict]:
    records = defaultdict(empty_record)
    counts = {}
    hashes = {}
    for filename, required in COLUMNS.items():
        path = data_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing {path}. Put all four CSVs in data/raw/.")
        count = 0
        with path.open(newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames or set(reader.fieldnames) != set(required):
                raise ValueError(f"Unexpected columns in {filename}: {reader.fieldnames}. Expected {required}.")
            for row_number, row in enumerate(reader, start=2):
                count += 1
                job_id = row["job_id"].strip()
                if not job_id.isdigit():
                    raise ValueError(f"Invalid job_id in {filename}:{row_number}: {job_id!r}")
                source = {"file": filename, "row": row_number}
                record = records[job_id]
                if filename == "job_skills.csv":
                    record["skills"].append({"value": row["skill_abr"].strip(), "source": source})
                elif filename == "job_industries.csv":
                    record["industries"].append({"value": row["industry_id"].strip(), "source": source})
                elif filename == "benefits.csv":
                    flag = row["inferred"].strip()
                    if flag not in ("0", "1"):
                        raise ValueError(f"Unexpected inferred flag in {filename}:{row_number}: {flag!r}")
                    record["benefits"].append({"value": row["type"].strip(), "inferred": flag, "source": source})
                else:
                    if not row["salary_id"].strip().isdigit():
                        raise ValueError(f"Invalid salary_id in {filename}:{row_number}")
                    for field in ("max_salary", "min_salary", "med_salary"):
                        raw = row[field].strip()
                        if raw:
                            try:
                                if not Decimal(raw).is_finite():
                                    raise ValueError("non-finite number")
                            except (InvalidOperation, ValueError) as exc:
                                raise ValueError(f"Invalid {field} in {filename}:{row_number}: {raw!r}") from exc
                    if row["pay_period"].strip() not in {"HOURLY", "DAILY", "WEEKLY", "BIWEEKLY", "MONTHLY", "YEARLY"}:
                        raise ValueError(f"Unexpected pay_period in {filename}:{row_number}")
                    # Keep salary figures as strings. Do not silently convert currency or pay periods.
                    values = {key: row[key].strip() for key in required if key != "job_id"}
                    record["salaries"].append({"values": values, "source": source})
        counts[filename] = count
        hashes[filename] = hash_file(path)
    return records, counts, hashes


def make_document(job_id: str, facts: dict) -> str:
    lines = [f"Job ID: {job_id}"]
    lines.append("Skills (codes only): " + (", ".join(x["value"] for x in facts["skills"]) or "not listed"))
    lines.append("Industry IDs (not industry names): " + (", ".join(x["value"] for x in facts["industries"]) or "not listed"))
    lines.append("Benefits (inferred flag 1 means inferred): " + (
        ", ".join(f"{x['value']} [inferred={x['inferred']}]" for x in facts["benefits"]) or "not listed"))
    if facts["salaries"]:
        for item in facts["salaries"]:
            lines.append("Salary as listed: " + "; ".join(f"{key}={value}" for key, value in item["values"].items() if value))
    else:
        lines.append("Salary: no salary row supplied")
    return "\n".join(lines)


def build_database(data_dir: Path, db_path: Path) -> dict:
    records, counts, hashes = load_records(data_dir)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()  # Rebuild from scratch; avoids stale records from a previous ingestion.
    with sqlite3.connect(db_path) as con:
        con.execute("CREATE TABLE jobs(job_id TEXT PRIMARY KEY, facts_json TEXT NOT NULL, document TEXT NOT NULL)")
        try:
            con.execute("CREATE VIRTUAL TABLE job_fts USING fts5(job_id UNINDEXED, document, tokenize='unicode61')")
        except sqlite3.OperationalError as exc:
            raise RuntimeError("SQLite FTS5 is required. Use a standard Python 3.11+ build with FTS5.") from exc
        con.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        # Commit chunks so larger datasets do not require one very large SQLite transaction.
        batch = []
        for job_id, facts in records.items():
            batch.append((job_id, json.dumps(facts, ensure_ascii=False), make_document(job_id, facts)))
            if len(batch) >= 2000:
                con.executemany("INSERT INTO jobs VALUES (?, ?, ?)", batch)
                con.executemany("INSERT INTO job_fts(job_id, document) VALUES (?, ?)", ((r[0], r[2]) for r in batch))
                batch.clear()
        if batch:
            con.executemany("INSERT INTO jobs VALUES (?, ?, ?)", batch)
            con.executemany("INSERT INTO job_fts(job_id, document) VALUES (?, ?)", ((r[0], r[2]) for r in batch))
        stats = {"source_rows": counts, "distinct_job_ids": len(records), "total_source_rows": sum(counts.values()), "source_sha256": hashes, "schema_version": 1}
        for key, value in stats.items():
            con.execute("INSERT INTO metadata VALUES (?, ?)", (key, json.dumps(value)))
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Load four CSV files into SQLite with source-row citations")
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--db", type=Path, default=Path("data/processed/jobs.sqlite"))
    args = parser.parse_args()
    print(json.dumps(build_database(args.data_dir, args.db), indent=2))
    print(f"Database ready: {args.db}")


if __name__ == "__main__":
    main()
