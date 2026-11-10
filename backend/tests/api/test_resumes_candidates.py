from sqlalchemy import select

from app.models import CandidateProfile, Resume, ResumeChunk
from helpers import SAMPLE_RESUME, create_job, make_docx, make_pdf, register


def upload(client, job_id, name="cv.pdf", data=None):
    data = data if data is not None else make_pdf(SAMPLE_RESUME)
    return client.post("/api/v1/resumes/upload", files={"file": (name, data, "application/pdf")},
                       data={"job_id": job_id} if job_id else {})


def test_recruiter_upload_parses_and_creates_application(client, db):
    register(client)
    job = create_job(client)
    r = upload(client, job["id"])
    assert r.status_code == 201, r.text
    res = r.json()
    st = client.get(f"/api/v1/resumes/{res['resume_id']}/status").json()
    assert st["parsing_status"] == "completed", st
    cand = client.get(f"/api/v1/candidates/{res['candidate_id']}").json()
    assert cand["full_name"] == "Ananya Krishnan"
    assert cand["email"] == "ananya.k@example.com"
    assert cand["total_experience_years"] == 2.6
    skills = {s["skill_key"]: s for s in cand["skills"]}
    assert skills["django"]["verification_status"] == "auto_extracted"
    assert skills["django"]["evidence_section"] == "skills"
    assert cand["applications"][0]["stage"] == "applied"
    chunks = db.scalars(select(ResumeChunk).where(ResumeChunk.resume_id == res["resume_id"])).all()
    assert chunks and all(c.embedding is not None and len(c.embedding) == 384 for c in chunks)
    apps = client.get(f"/api/v1/jobs/{job['id']}/applications").json()
    assert len(apps) == 1 and apps[0]["candidate_name"] == "Ananya Krishnan"


def test_recruiter_upload_requires_job(client):
    register(client)
    r = upload(client, None)
    assert r.status_code == 400 and r.json()["error"]["code"] == "job_required"


def test_docx_upload(client):
    register(client)
    job = create_job(client)
    r = client.post("/api/v1/resumes/upload", data={"job_id": job["id"]},
                    files={"file": ("cv.docx", make_docx(SAMPLE_RESUME),
                                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert r.status_code == 201
    assert client.get(f"/api/v1/resumes/{r.json()['resume_id']}/status").json()["parsing_status"] == "completed"


def test_bad_files_rejected(client):
    register(client)
    job = create_job(client)
    assert upload(client, job["id"], "virus.exe", b"MZ").json()["error"]["code"] == "unsupported_type"
    assert upload(client, job["id"], "fake.pdf", b"hello").json()["error"]["code"] == "bad_signature"
    assert upload(client, job["id"], "empty.pdf", b"").json()["error"]["code"] == "empty_file"
    big = b"%PDF-1.4\n" + b"0" * (10 * 1024 * 1024 + 10)
    r = upload(client, job["id"], "big.pdf", big)
    assert r.status_code == 413 and r.json()["error"]["code"] == "file_too_large"


def test_text_free_pdf_marked_failed(client):
    register(client)
    job = create_job(client)
    r = upload(client, job["id"], "blank.pdf", make_pdf(" "))
    st = client.get(f"/api/v1/resumes/{r.json()['resume_id']}/status").json()
    assert st["parsing_status"] == "failed" and "No text found" in st["parsing_error"]


def test_duplicate_file_same_job_and_other_job(client):
    register(client)
    job1 = create_job(client, title="Job One")
    job2 = create_job(client, title="Job Two")
    data = make_pdf(SAMPLE_RESUME)
    first = upload(client, job1["id"], data=data).json()
    dup = upload(client, job1["id"], data=data)
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "duplicate"
    linked = upload(client, job2["id"], data=data)
    assert linked.status_code == 201 and linked.json()["error_code"] == "duplicate_linked"
    assert linked.json()["candidate_id"] == first["candidate_id"]
    assert len(client.get(f"/api/v1/candidates/{first['candidate_id']}").json()["applications"]) == 2


def test_bulk_upload_mixed_results(client):
    register(client)
    job = create_job(client)
    other = SAMPLE_RESUME.replace("Ananya Krishnan", "Ravi Kumar").replace("ananya.k", "ravi.k")
    files = [("files", ("a.pdf", make_pdf(SAMPLE_RESUME), "application/pdf")),
             ("files", ("b.docx", make_docx(other), "application/octet-stream")),
             ("files", ("c.txt", b"hello", "text/plain"))]
    r = client.post(f"/api/v1/jobs/{job['id']}/resumes/bulk-upload", files=files)
    assert r.status_code == 207
    oks = [x["ok"] for x in r.json()]
    assert oks == [True, True, False]
    assert client.get(f"/api/v1/candidates?job_id={job['id']}").json()["total"] == 2


def test_profile_merge_by_email_with_registered_candidate(make_client, db):
    rec, cand = make_client(), make_client()
    register(rec)
    u = register(cand, role="candidate", email="ananya.k@example.com", name="Ananya K")
    job = create_job(rec)
    res = upload(rec, job["id"]).json()
    profiles = db.scalars(select(CandidateProfile)).all()
    assert len(profiles) == 1 and str(profiles[0].user_id) == u["id"]
    me = cand.get("/api/v1/candidates/me").json()
    assert me["full_name"] == "Ananya K"            # recruiter upload does not overwrite owner's name
    assert me["phone"] == "+91 98765 43210"          # but fills empty fields
    assert len(me["applications"]) == 1
    assert db.get(Resume, res["resume_id"]).candidate_id == profiles[0].id


def test_manual_correction_marks_verified_and_survives_reprocess(client):
    register(client)
    job = create_job(client)
    res = upload(client, job["id"]).json()
    cid = res["candidate_id"]
    up = client.put(f"/api/v1/candidates/{cid}", json={"full_name": "Ananya K. (corrected)", "total_experience_years": 3})
    assert up.status_code == 200
    assert up.json()["field_verification"]["full_name"] == "manually_verified"
    sk = client.put(f"/api/v1/candidates/{cid}/skills", json={"skills": [
        {"name": "Python"}, {"name": "FastAPI", "evidence_text": "Confirmed in call"}, {"name": "Quantum Basket Weaving"}]})
    assert sk.status_code == 200
    by = {s["skill_key"]: s for s in sk.json()}
    assert by["python"]["verification_status"] == "auto_extracted"     # unchanged one keeps status
    assert by["fastapi"]["verification_status"] == "manually_verified"
    assert by["quantum basket weaving"]["name"] == "Quantum Basket Weaving"
    assert "django" not in by
    assert client.post(f"/api/v1/resumes/{res['resume_id']}/reprocess").status_code == 200
    after = client.get(f"/api/v1/candidates/{cid}").json()
    assert after["full_name"] == "Ananya K. (corrected)"
    assert after["total_experience_years"] == 3
    keys = {s["skill_key"] for s in after["skills"]}
    assert {"fastapi", "quantum basket weaving", "django"} <= keys   # auto skills re-added, manual kept


def test_recruiter_cannot_see_other_recruiters_candidates(make_client):
    a, b = make_client(), make_client()
    register(a, email="a@example.com")
    register(b, email="b@example.com")
    job = create_job(a)
    res = upload(a, job["id"]).json()
    assert b.get(f"/api/v1/candidates/{res['candidate_id']}").status_code == 404
    assert b.get(f"/api/v1/resumes/{res['resume_id']}").status_code == 404
    assert b.get(f"/api/v1/resumes/{res['resume_id']}/file").status_code == 404
    assert b.put(f"/api/v1/candidates/{res['candidate_id']}", json={"full_name": "x"}).status_code == 404
    assert b.get("/api/v1/candidates").json()["total"] == 0
    assert b.post(f"/api/v1/jobs/{job['id']}/resumes/bulk-upload",
                  files=[("files", ("a.pdf", make_pdf("x y z " * 20), "application/pdf"))]).status_code == 404


def test_candidate_own_upload_apply_and_privacy(make_client):
    rec, c1, c2 = make_client(), make_client(), make_client()
    register(rec)
    register(c1, role="candidate", email="one@example.com")
    register(c2, role="candidate", email="two@example.com")
    job = create_job(rec)
    early = c1.post(f"/api/v1/jobs/{job['id']}/apply")
    assert early.status_code == 400 and early.json()["error"]["code"] == "resume_required"
    r = c1.post("/api/v1/resumes/upload", files={"file": ("me.pdf", make_pdf(SAMPLE_RESUME), "application/pdf")})
    assert r.status_code == 201
    me = c1.get("/api/v1/candidates/me").json()
    assert me["email"] == "one@example.com"  # account email kept
    assert c1.post(f"/api/v1/jobs/{job['id']}/apply").status_code == 201
    assert c1.post(f"/api/v1/jobs/{job['id']}/apply").status_code == 409
    assert len(c1.get("/api/v1/applications/me").json()) == 1
    assert c2.get(f"/api/v1/candidates/{me['id']}").status_code == 404
    assert c2.get(f"/api/v1/resumes/{r.json()['resume_id']}").status_code == 404
    assert c1.get("/api/v1/candidates").status_code == 403
    assert rec.get(f"/api/v1/candidates/{me['id']}").status_code == 200   # applied to recruiter's job


def test_resume_file_download(client):
    register(client)
    job = create_job(client)
    res = upload(client, job["id"]).json()
    f = client.get(f"/api/v1/resumes/{res['resume_id']}/file")
    assert f.status_code == 200 and f.content.startswith(b"%PDF") and f.headers["content-type"] == "application/pdf"


def test_candidate_filters_and_sort(client):
    register(client)
    job = create_job(client)
    upload(client, job["id"])
    other = SAMPLE_RESUME.replace("Ananya Krishnan", "Ravi Kumar").replace("ananya.k", "ravi.k").replace(
        "Django", "Spring Boot").replace("Jun 2022 - Dec 2024", "Jan 2015 - Dec 2024")
    upload(client, job["id"], "b.pdf", make_pdf(other))
    assert client.get("/api/v1/candidates?skill=django").json()["total"] == 1
    assert client.get("/api/v1/candidates?skill=springboot").json()["total"] == 1
    assert client.get("/api/v1/candidates?min_experience=5").json()["items"][0]["full_name"] == "Ravi Kumar"
    names = [c["full_name"] for c in client.get("/api/v1/candidates?sort=name").json()["items"]]
    assert names == ["Ananya Krishnan", "Ravi Kumar"]
    assert client.get("/api/v1/candidates?q=ravi").json()["total"] == 1
    assert client.get("/api/v1/candidates?sort=hack").status_code == 422


def test_delete_candidate_removes_files(client, db):
    register(client)
    job = create_job(client)
    res = upload(client, job["id"]).json()
    from app.utils.files import resolve_stored
    path = resolve_stored(db.get(Resume, res["resume_id"]).stored_path)
    assert path.exists()
    assert client.delete(f"/api/v1/candidates/{res['candidate_id']}").status_code == 204
    assert not path.exists()
    assert client.get(f"/api/v1/candidates/{res['candidate_id']}").status_code == 404
