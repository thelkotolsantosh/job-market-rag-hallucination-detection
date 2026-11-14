"""Question routing, retrieval, auditable answers and guardrails."""
from __future__ import annotations

import re
import sqlite3
from .store import find_job, first_job, search_jobs

JOB_ID_RE = re.compile(r"\b\d{7,15}\b")
SALARY_FIELDS = ("salary_id", "min_salary", "med_salary", "max_salary", "pay_period", "currency", "compensation_type")


def requested_job_id(question: str) -> str | None:
    found = JOB_ID_RE.search(question)
    return found.group(0) if found else None


def classify(question: str) -> str:
    q = question.lower()
    if any(x in q for x in ("company", "employer", "job title", "job description", "work location", "office address", "city")):
        return "unknown_field"
    if ("what does" in q or "meaning" in q or "expand" in q) and any(x in q for x in ("skill", "code", "industry")):
        return "unknown_field"
    if any(x in q for x in ("salary", "paid", "pay period", "compensation", "earn", "wage")):
        return "salaries"
    if any(x in q for x in ("benefit", "insurance", "401(k)", "tuition")):
        return "benefits"
    if any(x in q for x in ("industry", "industries")):
        return "industries"
    if any(x in q for x in ("skill", "skills")):
        return "skills"
    return "summary"


def evidence_claims(job: dict, intent: str) -> list[dict]:
    """Trusted claims derived only from CSV rows, never from model output."""
    result = []
    facts = job["facts"]
    categories = ("skills", "industries", "benefits", "salaries") if intent == "summary" else (intent,)
    for category in categories:
        if category == "skills":
            result.extend({"field": "skill_abr", "value": x["value"], "source": x["source"]} for x in facts["skills"])
        elif category == "industries":
            result.extend({"field": "industry_id", "value": x["value"], "source": x["source"]} for x in facts["industries"])
        elif category == "benefits":
            result.extend({"field": "benefit_type", "value": x["value"], "inferred": x["inferred"], "source": x["source"]} for x in facts["benefits"])
        elif category == "salaries":
            for x in facts["salaries"]:
                for field in SALARY_FIELDS:
                    value = x["values"].get(field, "")
                    if value:
                        result.append({"field": f"salary.{field}", "value": value, "source": x["source"]})
    return result


def render_claims(claims: list[dict], intent: str, job_id: str) -> str:
    if not claims:
        return f"No {intent} values are present in the uploaded CSVs for job {job_id}. This does not prove the job has none."
    chunks = []
    for claim in claims:
        extra = f" [inferred={claim['inferred']}]" if "inferred" in claim else ""
        src = claim["source"]
        chunks.append(f"{claim['field']}={claim['value']}{extra} ({src['file']}:{src['row']})")
    return f"For job {job_id}, the source records show: " + "; ".join(chunks) + "."


def answer(con: sqlite3.Connection, question: str, mode: str = "guarded", top_k: int = 5) -> dict:
    if mode not in {"guarded", "baseline", "ollama"}:
        raise ValueError("mode must be guarded, baseline, or ollama")
    if not question.strip():
        raise ValueError("question cannot be blank")
    if len(question) > 500:
        raise ValueError("question must be 500 characters or fewer")
    intent = classify(question)
    requested_id = requested_job_id(question)
    if mode != "baseline" and len(set(JOB_ID_RE.findall(question))) > 1:
        return abstain(question, mode, requested_id, "Please ask about one job ID at a time. Cross-job comparison is not supported in this demo.")
    if mode == "guarded" and intent == "unknown_field":
        return abstain(question, mode, requested_id, "The supplied files do not contain company names, job titles, descriptions, locations, or code definitions.")
    if mode == "ollama" and intent == "unknown_field":
        return abstain(question, mode, requested_id, "The requested field is not in the supplied files.")

    if requested_id:
        job = find_job(con, requested_id)
        method = "exact_job_id"
    else:
        matches = search_jobs(con, question, top_k=top_k)
        job = matches[0] if matches else None
        method = "fts5_bm25"
    if job is None and mode == "baseline":
        # Intentionally weak benchmark: blindly fall back to a different job instead of abstaining.
        # This is NOT an LLM and its error rate must not be marketed as an LLM hallucination rate.
        job = first_job(con)
        method = "unsafe_first_row_fallback"
    if job is None:
        return abstain(question, mode, requested_id, "No supporting job record was found in the uploaded files.")
    if intent == "unknown_field" and mode == "baseline":
        intent = "summary"  # Deliberately off-topic to expose a bad fallback.
    allowed_claims = evidence_claims(job, intent)
    if not allowed_claims:
        return abstain(question, mode, requested_id, f"No {intent} values were supplied for this job. That is not the same as proving none exist.", matched_id=job["job_id"])

    rejected = []
    if mode == "ollama":
        from .ollama_client import propose_claims, validate_model_claims
        proposals = propose_claims(question, job, allowed_claims)
        selected, rejected = validate_model_claims(proposals, allowed_claims)
        allowed_claims = selected
        if not selected:
            return abstain(question, mode, requested_id, "The model supplied no claims that passed source verification.", matched_id=job["job_id"], rejected=rejected)

    display_id = requested_id if mode == "baseline" and requested_id else job["job_id"]
    if not requested_id and mode != "baseline":
        prefix = "One matching job from full-text search (not a complete answer to every matching job): "
    else:
        prefix = ""
    return {
        "question": question, "mode": mode, "status": "answered", "requested_job_id": requested_id,
        "matched_job_id": job["job_id"], "retrieval": method,
        "answer": prefix + render_claims(allowed_claims, intent, display_id),
        "claims": allowed_claims,
        "citations": sorted({f"{x['source']['file']}:{x['source']['row']}" for x in allowed_claims}),
        "rejected_model_claims": rejected,
        "warning": "The baseline deliberately uses unsafe fallback retrieval. Its results are not LLM hallucinations." if mode == "baseline" else None,
    }


def abstain(question: str, mode: str, requested_id: str | None, message: str, matched_id: str | None = None, rejected: list | None = None) -> dict:
    return {"question": question, "mode": mode, "status": "abstained", "requested_job_id": requested_id,
            "matched_job_id": matched_id, "retrieval": None, "answer": message, "claims": [], "citations": [],
            "rejected_model_claims": rejected or [], "warning": None}
