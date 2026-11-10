from helpers import create_job, register

JD = """Backend Engineer
Requirements:
- 2+ years experience in Python, FastAPI and PostgreSQL
Nice to have:
- Docker, Kubernetes
"""


def test_create_list_get_update_delete(client):
    register(client)
    job = create_job(client, publish=False)
    assert job["status"] == "draft" and job["applicant_count"] == 0
    r = client.get("/api/v1/jobs")
    assert r.json()["total"] == 1
    body = {**{k: job[k] for k in ("title", "description", "required_skills", "preferred_skills")},
            "title": "Senior Backend Engineer", "minimum_experience": 4}
    up = client.put(f"/api/v1/jobs/{job['id']}", json=body)
    assert up.status_code == 200 and up.json()["title"] == "Senior Backend Engineer"
    assert up.json()["analysis_metadata"]["manually_edited"] is True
    assert client.delete(f"/api/v1/jobs/{job['id']}").status_code == 204
    assert client.get(f"/api/v1/jobs/{job['id']}").status_code == 404


def test_create_with_analysis_fills_fields(client):
    register(client)
    r = client.post("/api/v1/jobs", json={"title": "Backend Engineer", "description": JD, "analyze": True})
    j = r.json()
    assert {"Python", "FastAPI", "PostgreSQL"} <= set(j["required_skills"])
    assert {"Docker", "Kubernetes"} <= set(j["preferred_skills"])
    assert j["minimum_experience"] == 2


def test_analyze_endpoint_preview_and_apply(client):
    register(client)
    job = create_job(client, required=["Java"], publish=False)
    prev = client.post(f"/api/v1/jobs/{job['id']}/analyze", json={"description": JD})
    assert "FastAPI" in prev.json()["required_skills"]
    assert client.get(f"/api/v1/jobs/{job['id']}").json()["required_skills"] == ["Java"]  # preview only
    client.post(f"/api/v1/jobs/{job['id']}/analyze", json={"description": JD, "apply": True})
    assert "FastAPI" in client.get(f"/api/v1/jobs/{job['id']}").json()["required_skills"]


def test_publish_requires_required_skills(client):
    register(client)
    job = create_job(client, required=[], publish=False)
    r = client.post(f"/api/v1/jobs/{job['id']}/publish")
    assert r.status_code == 400 and r.json()["error"]["code"] == "missing_required_skills"


def test_validation_errors(client):
    register(client)
    r = client.post("/api/v1/jobs", json={"title": "x", "minimum_experience": -1,
                                          "education_requirements": [{"level": "wizard"}]})
    assert r.status_code == 422
    fields = {d["field"] for d in r.json()["error"]["details"]}
    assert {"title", "minimum_experience", "education_requirements.0.level"} <= fields


def test_recruiter_isolation(make_client):
    a, b = make_client(), make_client()
    register(a, email="a@example.com")
    register(b, email="b@example.com")
    job = create_job(a)
    assert b.get(f"/api/v1/jobs/{job['id']}").status_code == 404
    assert b.put(f"/api/v1/jobs/{job['id']}", json={"title": "Hacked"}).status_code == 404
    assert b.delete(f"/api/v1/jobs/{job['id']}").status_code == 404
    assert b.get("/api/v1/jobs").json()["total"] == 0


def test_candidate_sees_only_published_and_cannot_create(make_client):
    rec, cand = make_client(), make_client()
    register(rec)
    register(cand, role="candidate")
    create_job(rec, title="Open role")
    draft = create_job(rec, title="Draft role", publish=False)
    titles = [j["title"] for j in cand.get("/api/v1/jobs").json()["items"]]
    assert titles == ["Open role"]
    assert cand.get(f"/api/v1/jobs/{draft['id']}").status_code == 404
    assert cand.post("/api/v1/jobs", json={"title": "Mine"}).status_code == 403


def test_search_and_pagination(client):
    register(client)
    for i in range(5):
        create_job(client, title=f"Role {i}", publish=False)
    create_job(client, title="Data Scientist", publish=False)
    p = client.get("/api/v1/jobs?page=2&page_size=4").json()
    assert p["total"] == 6 and len(p["items"]) == 2
    assert client.get("/api/v1/jobs?q=scientist").json()["total"] == 1


def test_unauthenticated_and_bad_id(client):
    assert client.get("/api/v1/jobs").status_code == 401
    register(client)
    assert client.get("/api/v1/jobs/not-a-uuid").status_code == 422
    assert client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000").status_code == 404
