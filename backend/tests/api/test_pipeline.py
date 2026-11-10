from helpers import SAMPLE_RESUME, create_job, make_pdf, register


def _setup(client):
    register(client)
    job = create_job(client)
    r = client.post("/api/v1/resumes/upload", data={"job_id": job["id"]},
                    files={"file": ("cv.pdf", make_pdf(SAMPLE_RESUME), "application/pdf")})
    return job, r.json()["application_id"]


def test_stage_changes_are_logged(client):
    job, app_id = _setup(client)
    r = client.patch(f"/api/v1/applications/{app_id}/stage", json={"stage": "shortlisted", "note": "Strong Python"})
    assert r.status_code == 200 and r.json()["stage"] == "shortlisted"
    client.patch(f"/api/v1/applications/{app_id}/stage", json={"stage": "interview_scheduled"})
    h = client.get(f"/api/v1/applications/{app_id}/history").json()
    assert [(x["from_stage"], x["to_stage"]) for x in h] == [
        (None, "applied"), ("applied", "shortlisted"), ("shortlisted", "interview_scheduled")]
    assert h[1]["note"] == "Strong Python" and h[1]["changed_by_name"] == "Test User"


def test_invalid_and_same_stage(client):
    _, app_id = _setup(client)
    assert client.patch(f"/api/v1/applications/{app_id}/stage", json={"stage": "hired"}).status_code == 422
    r = client.patch(f"/api/v1/applications/{app_id}/stage", json={"stage": "applied"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "same_stage"


def test_stage_change_permissions(make_client):
    a, b, c = make_client(), make_client(), make_client()
    _, app_id = _setup(a)
    register(b, email="b@example.com")
    register(c, role="candidate", email="c@example.com")
    assert b.patch(f"/api/v1/applications/{app_id}/stage", json={"stage": "rejected"}).status_code == 404
    assert c.patch(f"/api/v1/applications/{app_id}/stage", json={"stage": "selected"}).status_code == 403
    assert b.get(f"/api/v1/applications/{app_id}/history").status_code == 404


def test_remove_application_deletes_orphan_placeholder(client):
    job, app_id = _setup(client)
    assert client.delete(f"/api/v1/applications/{app_id}").status_code == 204
    assert client.get("/api/v1/candidates").json()["total"] == 0
    assert client.get(f"/api/v1/jobs/{job['id']}/applications").json() == []


def test_never_auto_rejected(client):
    _, app_id = _setup(client)
    apps = client.get("/api/v1/candidates").json()["items"][0]["applications"]
    assert apps[0]["stage"] == "applied"
