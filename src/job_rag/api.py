"""Interactive API. Open http://localhost:8000/docs after starting Uvicorn."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .rag import answer
from .store import connect, find_job, search_jobs, stats

app = FastAPI(title="Job Market RAG with Hallucination Guardrails", version="0.1.0",
              description="Source-cited questions over skills, benefits, salary records and industry IDs.")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500, examples=["What skills are listed for job 3884428798?"])
    mode: Literal["guarded", "baseline", "ollama"] = "guarded"
    top_k: int = Field(default=5, ge=1, le=20)


def db_path() -> Path:
    return Path(os.environ.get("DB_PATH", "data/processed/jobs.sqlite"))


@app.get("/health")
def health():
    try:
        con = connect(db_path())
        try:
            con.execute("SELECT 1")
        finally:
            con.close()
    except (FileNotFoundError, OSError):
        raise HTTPException(503, "Database missing. Run ingestion first.")
    return {"status": "ok", "database": "ready"}


@app.get("/stats")
def get_stats():
    try:
        con = connect(db_path())
        try:
            return stats(con)
        finally:
            con.close()
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    try:
        con = connect(db_path())
        try:
            job = find_job(con, job_id)
        finally:
            con.close()
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc)) from exc
    if not job:
        raise HTTPException(404, "This job ID was not found in the uploaded CSV files.")
    return job


@app.post("/ask")
def ask(request: AskRequest):
    try:
        con = connect(db_path())
        try:
            return answer(con, request.question, mode=request.mode, top_k=request.top_k)
        finally:
            con.close()
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(502, str(exc)) from exc


@app.get("/", include_in_schema=False)
def home():
    page = Path(__file__).resolve().parents[2] / "web" / "index.html"
    if not page.is_file():
        raise HTTPException(404, "Web demo file not installed. Try /docs instead.")
    return FileResponse(page)


@app.get("/search")
def search(q: str = Query(min_length=1, max_length=200), limit: int = Query(default=5, ge=1, le=20)):
    try:
        con = connect(db_path())
        try:
            jobs = search_jobs(con, q, top_k=limit)
        finally:
            con.close()
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc)) from exc
    return {"query": q, "retrieval": "sqlite_fts5_bm25", "results": [
        {"job_id": job["job_id"], "document": job["document"]} for job in jobs
    ]}
