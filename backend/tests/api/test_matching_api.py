from helpers import SAMPLE_RESUME, create_job, make_pdf, register

FRONTEND = """Meera Iyer
meera.i@example.com | +91 90000 11111
SKILLS
JavaScript, React, HTML, CSS, Figma
EXPERIENCE
Frontend Developer | Pixel Co
Jan 2021 - Dec 2024
- Built React dashboards and design systems.
EDUCATION
B.Sc. Mathematics
Some College | 2017 - 2020
"""


def _upload(client, job_id, text, name):
    r = client.post("/api/v1/resumes/upload", data={"job_id": job_id},
                    files={"file": (name, make_pdf(text), "application/pdf")})
    assert r.status_code == 201, r.text
    return r.json()


def test_run_rank_and_explain(client):
    register(client)
    job = create_job(client, required=["Python", "FastAPI", "PostgreSQL", "REST APIs"], min_exp=2,
                     education_requirements=[{"level": "bachelors", "fields": ["computer science"]}])
    backend = _upload(client, job["id"], SAMPLE_RESUME, "a.pdf")
    _upload(client, job["id"], FRONTEND, "b.pdf")
    run = client.post(f"/api/v1/matching/jobs/{job['id']}/run").json()
    assert run["scored"] == 2 and run["skipped_no_parsed_resume"] == 0
    res = client.get(f"/api/v1/matching/jobs/{job['id']}/results").json()
    assert [r["candidate_name"] for r in res] == ["Ananya Krishnan", "Meera Iyer"]
    top = res[0]
    assert top["rank"] == 1 and top["overall_score"] > res[1]["overall_score"]
    ex = top["explanation"]
    assert {b["component"] for b in ex["breakdown"]} == {"semantic", "required_skills", "preferred_skills",
                                                         "experience", "education", "certifications"}
    assert abs(sum(b["contribution"] for b in ex["breakdown"]) - top["overall_score"]) < 0.1
    assert any(m["skill"] == "Python" and m["evidence_text"] for m in ex["required_skills"]["matched"])
    assert "not a probability" in ex["semantic"]["note"].lower()
    assert ex["embedding_model"].endswith("all-MiniLM-L6-v2")
    detail = client.get(f"/api/v1/matching/{top['id']}").json()
    assert detail["application_id"] == backend["application_id"]
    # missing / related skills get RAG evidence: the closest resume text
    low = res[1]["explanation"]["required_skills"]
    assert low["missing"] and low["closest_evidence"]
    assert {"section", "text", "similarity"} <= set(low["closest_evidence"][0])


def test_rerun_updates_instead_of_duplicating(client):
    register(client)
    job = create_job(client)
    _upload(client, job["id"], SAMPLE_RESUME, "a.pdf")
    client.post(f"/api/v1/matching/jobs/{job['id']}/run")
    client.post(f"/api/v1/matching/jobs/{job['id']}/run")
    assert len(client.get(f"/api/v1/matching/jobs/{job['id']}/results").json()) == 1


def test_custom_weights_are_used(client):
    register(client)
    job = create_job(client)
    _upload(client, job["id"], SAMPLE_RESUME, "a.pdf")
    bad = client.put("/api/v1/settings/weights", json={"weights": {"semantic": 90}})
    assert bad.status_code == 422
    w = {"semantic": 0, "required_skills": 100, "preferred_skills": 0, "experience": 0, "education": 0, "certifications": 0}
    assert client.put("/api/v1/settings/weights", json={"weights": w}).status_code == 200
    client.post(f"/api/v1/matching/jobs/{job['id']}/run")
    r = client.get(f"/api/v1/matching/jobs/{job['id']}/results").json()[0]
    assert r["weights_used"]["required_skills"] == 100
    assert r["overall_score"] == round(r["components"]["required_skills"] * 100, 1)


def test_compare(client):
    register(client)
    job = create_job(client)
    a = _upload(client, job["id"], SAMPLE_RESUME, "a.pdf")
    b = _upload(client, job["id"], FRONTEND, "b.pdf")
    client.post(f"/api/v1/matching/jobs/{job['id']}/run")
    c = client.post("/api/v1/matching/compare", json={"job_id": job["id"],
                                                     "candidate_ids": [a["candidate_id"], b["candidate_id"]]}).json()
    py = next(r for r in c["skill_matrix"] if r["skill"] == "Python")
    assert [x["status"] for x in py["candidates"]] == ["matched", "missing"]
    one = client.post("/api/v1/matching/compare", json={"job_id": job["id"], "candidate_ids": [a["candidate_id"]]})
    assert one.status_code == 422


def test_matching_permissions(make_client):
    a, b, cand = make_client(), make_client(), make_client()
    register(a, email="a@example.com")
    register(b, email="b@example.com")
    job = create_job(a)
    _upload(a, job["id"], SAMPLE_RESUME, "a.pdf")
    a.post(f"/api/v1/matching/jobs/{job['id']}/run")
    mid = a.get(f"/api/v1/matching/jobs/{job['id']}/results").json()[0]["id"]
    assert b.post(f"/api/v1/matching/jobs/{job['id']}/run").status_code == 404
    assert b.get(f"/api/v1/matching/{mid}").status_code == 404
    register(cand, role="candidate", email="other@example.com")
    assert cand.get(f"/api/v1/matching/{mid}").status_code == 404
    assert cand.post(f"/api/v1/matching/jobs/{job['id']}/run").status_code == 403


def test_candidate_sees_own_match(make_client):
    rec, cand = make_client(), make_client()
    register(rec)
    register(cand, role="candidate", email="ananya.k@example.com")
    job = create_job(rec)
    _upload(rec, job["id"], SAMPLE_RESUME, "a.pdf")
    rec.post(f"/api/v1/matching/jobs/{job['id']}/run")
    mid = cand.get("/api/v1/applications/me").json()[0]["match_id"]
    assert cand.get(f"/api/v1/matching/{mid}").status_code == 200


def test_llm_status_reports_none(client):
    register(client)
    s = client.get("/api/v1/settings/llm-status").json()
    assert s["provider"] == "none" and s["available"] is False
    assert "key" not in str(s).lower() or "api_key" not in s
