"""Small tests run on GitHub Actions without loading the full dataset."""
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from job_rag import api
from job_rag.ingest import build_database
from job_rag.ollama_client import validate_model_claims
from job_rag.rag import answer
from job_rag.store import connect, find_job, search_jobs, stats
from job_rag.evaluate import make_benchmark, score

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def database(tmp_path):
    db = tmp_path / "jobs.sqlite"
    build_database(FIXTURES, db)
    return db


def test_ingestion_counts_and_source_rows(database):
    with connect(database) as con:
        s = stats(con)
        assert s["total_source_rows"] == 8
        assert s["distinct_job_ids"] == 2
        assert len(s["source_sha256"]["benefits.csv"]) == 64
        doc = find_job(con, "10000001")
        assert doc["facts"]["benefits"][0]["source"] == {"file": "benefits.csv", "row": 2}


def test_guarded_skills_are_cited(database):
    with connect(database) as con:
        result = answer(con, "What skills are listed for job 10000001?")
        assert result["status"] == "answered"
        assert {c["value"] for c in result["claims"]} == {"IT", "ENG"}
        assert "job_skills.csv:2" in result["citations"]


def test_no_invented_company_or_missing_job(database):
    with connect(database) as con:
        for q in ("What company posted job 10000001?", "What skills are listed for job 999999999990000?"):
            result = answer(con, q)
            assert result["status"] == "abstained"
            assert result["claims"] == []


def test_no_salary_does_not_mean_zero_salary(database):
    with connect(database) as con:
        result = answer(con, "What salary is listed for job 10000002?")
        assert result["status"] == "abstained"
        assert "not the same as proving none exist" in result["answer"]


def test_baseline_is_intentionally_unsafe(database):
    with connect(database) as con:
        result = answer(con, "What skills are listed for job 999999999990000?", "baseline")
        assert result["status"] == "answered"
        assert result["matched_job_id"] != result["requested_job_id"]


def test_search_is_lexical_and_sql_injection_safe(database):
    with connect(database) as con:
        assert search_jobs(con, "medical insurance")[0]["job_id"] == "10000001"
        search_jobs(con, "\"; DROP TABLE jobs; --")
        assert find_job(con, "10000002") is not None


def test_model_claim_validation_restores_real_source(database):
    with connect(database) as con:
        from job_rag.rag import evidence_claims
        allowed = evidence_claims(find_job(con, "10000001"), "skills")
    proposed = [{"field": "skill_abr", "value": "IT", "source": {"file": "fake.csv", "row": 99}},
                {"field": "skill_abr", "value": "MAGIC"}, {"field": "company", "value": "MadeUp"}]
    accepted, rejected = validate_model_claims(proposed, allowed)
    assert len(accepted) == 1 and len(rejected) == 2
    assert accepted[0]["source"] == {"file": "job_skills.csv", "row": 2}


def test_benchmark_reduces_unsupported_claims(database):
    with connect(database) as con:
        cases = make_benchmark(con, 1)
        before, _ = score(con, cases, "baseline")
        after, _ = score(con, cases, "guarded")
    assert len(cases) >= 7
    assert before["counts"]["unsupported_claims"] > 0
    assert after["counts"]["unsupported_claims"] == 0
    assert after["counts"]["correct_abstentions"] > 0


def test_api_endpoints(database, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(database))
    client = TestClient(api.app)
    assert client.get("/health").status_code == 200
    assert client.get("/stats").json()["distinct_job_ids"] == 2
    assert client.get("/jobs/10000001").status_code == 200
    assert client.get("/jobs/999999999").status_code == 404
    response = client.post("/ask", json={"question": "What salary is listed for job 10000001?"})
    assert response.status_code == 200
    assert any(c["field"] == "salary.currency" and c["value"] == "USD" for c in response.json()["claims"])
    assert client.get("/").status_code == 200


def test_question_length_validation(database):
    with connect(database) as con:
        with pytest.raises(ValueError):
            answer(con, "x" * 501)


def test_multiple_ids_are_not_silently_compared(database):
    with connect(database) as con:
        result = answer(con, "Compare skills for job 10000001 and job 10000002")
        assert result["status"] == "abstained"


def test_bad_model_claim_type_is_rejected(database):
    with connect(database) as con:
        from job_rag.rag import evidence_claims
        allowed = evidence_claims(find_job(con, "10000001"), "skills")
    accepted, rejected = validate_model_claims([{"field": "skill_abr", "value": ["IT"]}], allowed)
    assert accepted == [] and len(rejected) == 1


def test_manual_review_calculator(tmp_path):
    from job_rag.evaluate_manual import score_manual
    path = tmp_path / "labels.csv"
    path.write_text("answer_id,model,atomic_claim,source_ref,supported\n"
                    "a1,local,Salary is 100,source.csv:2,yes\n"
                    "a1,local,Company is Z,,no\n"
                    "a2,local,No fact,,uncertain\n", encoding="utf-8")
    metrics = score_manual(path)
    assert metrics["models"]["local"]["unsupported_claim_rate_pct"] == 50.0
    assert metrics["models"]["local"]["answer_hallucination_rate_pct"] == 100.0
    assert metrics["unlabeled_or_uncertain_rows"] == 1
