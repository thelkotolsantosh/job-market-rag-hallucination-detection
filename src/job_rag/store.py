"""Read-only SQLite retrieval and evidence extraction."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

STOPWORDS = {"a", "and", "any", "are", "can", "do", "does", "find", "for", "from", "give", "have", "in", "is", "job", "jobs", "list", "me", "of", "on", "please", "show", "the", "these", "this", "to", "what", "which", "with", "about", "tell", "some", "are", "that"}


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"Database not found: {path}. First run: python -m job_rag.ingest")
    con = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def find_job(con: sqlite3.Connection, job_id: str) -> dict | None:
    row = con.execute("SELECT job_id, facts_json, document FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    return {"job_id": row["job_id"], "facts": json.loads(row["facts_json"]), "document": row["document"]} if row else None


def search_jobs(con: sqlite3.Connection, query: str, top_k: int = 5) -> list[dict]:
    """Rank lexical matches using FTS5, not semantic/vector embeddings."""
    terms = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", query) if w.lower() not in STOPWORDS]
    terms = list(dict.fromkeys(terms))[:10]
    if not terms:
        return []
    # Escaped quoted terms prevent FTS query syntax from being treated as executable syntax.
    expression = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
    rows = con.execute("SELECT job_id FROM job_fts WHERE job_fts MATCH ? ORDER BY bm25(job_fts) LIMIT ?", (expression, min(max(top_k, 1), 20))).fetchall()
    return [job for row in rows if (job := find_job(con, row["job_id"])) is not None]


def first_job(con: sqlite3.Connection) -> dict | None:
    row = con.execute("SELECT job_id FROM jobs ORDER BY job_id LIMIT 1").fetchone()
    return find_job(con, row["job_id"]) if row else None


def stats(con: sqlite3.Connection) -> dict:
    return {r["key"]: json.loads(r["value"]) for r in con.execute("SELECT key,value FROM metadata")}
