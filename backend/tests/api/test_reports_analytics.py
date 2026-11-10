import json

import pytest
from sqlalchemy import select

from app.ai.agents.learning_agent import load_resources
from app.ai.providers import set_provider_override
from app.ai.providers.fake import FakeProvider
from helpers import SAMPLE_RESUME, create_job, make_pdf, register
from tests.api.test_interviews import fake_responder


@pytest.fixture
def fake_llm():
    set_provider_override(FakeProvider(fake_responder))
    yield
    set_provider_override(None)


def full_setup(make_client):
    rec, cand = make_client(), make_client()
    register(rec)
    register(cand, role="candidate", email="ananya.k@example.com")
    job = create_job(rec, required=["Python", "FastAPI", "PostgreSQL", "Kubernetes"])
    r = rec.post("/api/v1/resumes/upload", data={"job_id": job["id"]},
                 files={"file": ("cv.pdf", make_pdf(SAMPLE_RESUME), "application/pdf")}).json()
    rec.post(f"/api/v1/matching/jobs/{job['id']}/run")
    return rec, cand, job, r


def run_interview(rec, cand, app_id):
    iid = rec.post("/api/v1/interviews", json={"application_id": app_id, "interview_type": "assigned",
                                               "question_count": 3, "categories": ["programming"]}).json()["id"]
    rec.post(f"/api/v1/interviews/{iid}/generate-questions")
    cur = cand.post(f"/api/v1/interviews/{iid}/start").json()
    while not cur.get("done"):
        cand.post(f"/api/v1/interviews/{iid}/answers/{cur['question']['id']}",
                  json={"text": "REST endpoints with validation and correct status codes for errors."})
        cur = cand.get(f"/api/v1/interviews/{iid}/current").json()
    cand.post(f"/api/v1/interviews/{iid}/complete")
    return iid


def test_report_generate_notes_and_pdf(make_client, fake_llm):
    rec, cand, job, r = full_setup(make_client)
    iid = run_interview(rec, cand, r["application_id"])
    rep = rec.post("/api/v1/reports/generate", json={"application_id": r["application_id"]})
    assert rep.status_code == 201, rep.text
    rep = rep.json()
    d = rep["report_data"]
    assert d["candidate"]["name"] == "Test User"  # registered candidate keeps their own name
    assert d["match"]["overall_score"] is not None
    assert d["interview"]["id"] == iid and d["interview"]["total_score"] is not None
    assert any(x["skill"] == "Kubernetes" for x in d["learning_recommendations"])
    urls = {res["url"] for items in load_resources().values() for res in items}
    assert all(x["url"] in urls for x in d["learning_recommendations"])          # never invented
    assert any("not a probability" in lim for lim in d["limitations"])
    assert "report-1.0" in rep["methodology_version"]
    n = rec.post(f"/api/v1/reports/{rep['id']}/notes", json={"text": "Strong backend fit; verify K8s in round 2."}).json()
    assert n["notes"][0]["label"] == "Recruiter comment" and n["notes"][0]["author"] == "Test User"
    pdf = rec.get(f"/api/v1/reports/{rep['id']}/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF") and len(pdf.content) > 3000
    from app.ai.parsing.extract import extract_pdf
    text, _ = extract_pdf(pdf.content)
    assert "Recruiter comments" in text and "verify K8s" in text and "Test User" in text
    lst = rec.get("/api/v1/reports?q=test").json()
    assert lst["total"] == 1 and lst["items"][0]["interview_score"] is not None


def test_report_permissions_and_preconditions(make_client):
    rec, cand, job, r = full_setup(make_client)
    other = make_client()
    register(other, email="o@example.com")
    rep = rec.post("/api/v1/reports/generate", json={"application_id": r["application_id"]}).json()
    assert other.get(f"/api/v1/reports/{rep['id']}").status_code == 404
    assert other.get(f"/api/v1/reports/{rep['id']}/pdf").status_code == 404
    assert cand.get(f"/api/v1/reports/{rep['id']}").status_code == 403
    assert other.post("/api/v1/reports/generate", json={"application_id": r["application_id"]}).status_code == 404
    job2 = create_job(rec, title="Empty")
    r2 = rec.post("/api/v1/resumes/upload", data={"job_id": job2["id"]},
                  files={"file": ("x.pdf", make_pdf(SAMPLE_RESUME.replace("ananya.k", "z")), "application/pdf")}).json()
    nothing = rec.post("/api/v1/reports/generate", json={"application_id": r2["application_id"]})
    assert nothing.status_code == 400 and nothing.json()["error"]["code"] == "nothing_to_report"


def test_analytics_match_database(make_client, fake_llm, db):
    rec, cand, job, r = full_setup(make_client)
    empty = make_client()
    register(empty, email="empty@example.com")
    e = empty.get("/api/v1/analytics/overview").json()
    assert e["total_jobs"] == 0 and e["average_match_score"] is None and [a["action"] for a in e["recent_activity"]] == ["user.registered"]
    run_interview(rec, cand, r["application_id"])
    o = rec.get("/api/v1/analytics/overview").json()
    from app.models import CandidateMatch
    m = db.scalar(select(CandidateMatch))
    assert o["total_jobs"] == 1 and o["active_jobs"] == 1 and o["total_candidates"] == 1
    assert o["resumes_processed"] == 1 and o["interviews_completed"] == 1
    assert o["average_match_score"] == round(m.overall_score, 1)
    assert o["recent_activity"][0]["action"].startswith("interview.")
    pipe = {p["stage"]: p["count"] for p in rec.get("/api/v1/analytics/pipeline").json()}
    assert pipe["interview_completed"] == 1 and sum(pipe.values()) == 1
    jobs = rec.get("/api/v1/analytics/jobs").json()
    assert jobs[0]["applicants"] == 1 and jobs[0]["best_score"] == m.overall_score
    skills = {s["skill"]: s for s in rec.get("/api/v1/analytics/skills").json()}
    assert skills["Python"]["demand"] == 1 and skills["Python"]["candidates_with_skill"] == 1
    assert skills["Kubernetes"]["candidates_with_skill"] == 0
    trend = rec.get("/api/v1/analytics/interviews").json()
    assert trend[0]["completed"] == 1
    assert cand.get("/api/v1/analytics/overview").status_code == 403


def test_learning_recommendations_and_progress(make_client):
    rec, cand, job, r = full_setup(make_client)
    app_id = cand.get("/api/v1/applications/me").json()[0]["id"]
    recs = cand.get(f"/api/v1/learning/recommendations?application_id={app_id}").json()
    assert recs["matched"] and recs["items"][0]["skill"] == "Kubernetes" and recs["items"][0]["priority"] in ("required", "related")
    key = recs["items"][0]["key"]
    assert cand.post("/api/v1/learning/progress", json={"resource_key": key}).status_code == 200
    again = cand.get(f"/api/v1/learning/recommendations?application_id={app_id}").json()
    assert next(i for i in again["items"] if i["key"] == key)["completed"] is True
    cand.post("/api/v1/learning/progress", json={"resource_key": key, "completed": False})
    assert cand.post("/api/v1/learning/progress", json={"resource_key": "made-up"}).status_code == 404


def test_skill_graph(make_client):
    rec, cand, job, r = full_setup(make_client)
    cid = rec.get(f"/api/v1/jobs/{job['id']}/applications").json()[0]["candidate_id"]  # merged profile id
    g = rec.get(f"/api/v1/candidates/{cid}/skill-graph?job_id={job['id']}").json()
    kinds = {n["id"]: n["kind"] for n in g["nodes"]}
    assert kinds["python"] == "matched" and kinds["kubernetes"] in ("missing", "related_only")
    assert kinds["fastapi"] == "matched"
    from app.ai.taxonomy import get_taxonomy
    tax = get_taxonomy()
    for e in g["edges"]:
        assert tax.are_related(e["source"], e["target"])       # only taxonomy links
    k8s = next(p for p in g["learning_paths"] if p["target"] == "Kubernetes")
    assert k8s["path"][-1] == "Kubernetes" and k8s["path"][0] in {"Docker", "Microservices"}
    other = make_client()
    register(other, email="o@example.com")
    assert other.get(f"/api/v1/candidates/{cid}/skill-graph?job_id={job['id']}").status_code == 404


def test_ai_audit_listing(make_client, fake_llm):
    rec, cand, job, r = full_setup(make_client)
    run_interview(rec, cand, r["application_id"])
    a = rec.get("/api/v1/ai-audit").json()
    agents = {i["agent"] for i in a["items"]}
    assert {"interview_generation", "interview_evaluation"} <= agents
    gen = next(i for i in a["items"] if i["agent"] == "interview_generation")
    assert gen["provider"] == "fake-test-double" and gen["prompt_version"] == "qgen-1.0" and gen["validation_passed"]
    other = make_client()
    register(other, email="o@example.com")
    assert other.get("/api/v1/ai-audit").json()["total"] == 0
