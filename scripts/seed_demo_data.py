"""Load the SYNTHETIC demo data into the database through the real pipeline.

Creates:
  - recruiter  demo.recruiter@example.com / DemoPass123
  - candidate  aarav.raman@example.com    / DemoPass123  (owns synthetic resume cand01)
  - 10 published synthetic jobs (analyzed by the Job Analysis Agent)
  - 30 synthetic resumes, uploaded and parsed like real uploads; each candidate is added to the job
    of their role family and to one adjacent job
  - matching results for every job
Every created job and candidate profile is marked is_synthetic = true.

Idempotent: if the demo recruiter already exists, nothing is changed.
Use --reset to delete the demo accounts and everything they own, then seed again.

Usage (from the backend folder, venv active):
  python ../scripts/seed_demo_data.py [--reset]
Run `python ../scripts/generate_synthetic_data.py` first if sample_data/ is empty.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")

from sqlalchemy import select  # noqa: E402

from app.ai.agents.job_agent import JobAnalysisAgent  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database.session import SessionLocal  # noqa: E402
from app.models import CandidateProfile, Job, Resume, User  # noqa: E402
from app.models.enums import JobStatus, Role  # noqa: E402
from app.services import matching_service, resume_service  # noqa: E402
from app.services.auth_service import link_or_create_candidate_profile  # noqa: E402
from app.services.job_service import apply_analysis  # noqa: E402
from app.utils.files import resolve_stored  # noqa: E402

RECRUITER = "demo.recruiter@example.com"
CANDIDATE = "aarav.raman@example.com"
PASSWORD = "DemoPass123"
ADJ = {
    "python_backend": "fullstack_js", "java_backend": "python_backend", "frontend": "fullstack_js",
    "fullstack_js": "frontend", "data_science": "ml_nlp", "ml_nlp": "data_science",
    "data_engineering": "data_science", "devops": "python_backend", "mobile": "frontend",
    "qa_automation": "python_backend",
}


def reset(db) -> None:
    rec = db.scalar(select(User).where(User.email == RECRUITER))
    cand_user = db.scalar(select(User).where(User.email == CANDIDATE))
    profiles = db.scalars(select(CandidateProfile).where(CandidateProfile.is_synthetic.is_(True))).all()
    paths = []
    for p in profiles:
        paths += [r.stored_path for r in db.scalars(select(Resume).where(Resume.candidate_id == p.id)).all()]
        db.delete(p)
    if rec:
        db.delete(rec)  # cascades to jobs, applications, matches, interviews, reports
    if cand_user:
        db.delete(cand_user)
    db.commit()
    for sp in paths:
        try:
            resolve_stored(sp).unlink(missing_ok=True)
        except Exception:
            pass
    print(f"Reset: removed demo accounts and {len(profiles)} synthetic profiles.")


def seed(db) -> None:
    jobs_data = json.loads((ROOT / "sample_data/synthetic_jobs/jobs.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "sample_data/synthetic_candidates/manifest.json").read_text(encoding="utf-8"))

    rec = User(name="Demo Recruiter", email=RECRUITER, password_hash=hash_password(PASSWORD), role=Role.RECRUITER)
    db.add(rec)
    cuser = User(name="Aarav Raman", email=CANDIDATE, password_hash=hash_password(PASSWORD), role=Role.CANDIDATE)
    db.add(cuser)
    db.flush()
    link_or_create_candidate_profile(db, cuser)
    db.commit()

    jobs: dict[str, Job] = {}
    for j in jobs_data:
        job = Job(recruiter_id=rec.id, title=j["title"], department=j["department"], description=j["description"],
                  status=JobStatus.PUBLISHED, is_synthetic=True)
        a = JobAnalysisAgent().analyze(j["description"], j["title"])
        apply_analysis(job, a, only_empty=False)
        job.analysis_metadata = {"method": a.method, "agent_version": JobAnalysisAgent.version, "synthetic": True}
        db.add(job)
        db.flush()
        jobs[j["archetype"]] = job
    db.commit()
    print(f"Created {len(jobs)} jobs.")

    for m in manifest:
        path = ROOT / "sample_data/synthetic_candidates" / m["file"]
        data = path.read_bytes()
        for arch in (m["archetype"], ADJ[m["archetype"]]):
            res = resume_service.upload_resume(db, rec, m["file"], data, jobs[arch].id)
            if res.ok and res.error_code != "duplicate_linked":
                resume_service.process_resume(db, res.resume_id)
            if not res.ok:
                print(f"  ! {m['file']}: {res.error}")
        print(f"  {m['file']}: uploaded and parsed")

    for p in db.scalars(select(CandidateProfile)).all():
        emails = {x["email"] for x in manifest}
        if p.email in emails:
            p.is_synthetic = True
    db.commit()

    for arch, job in jobs.items():
        r = matching_service.run_for_job(db, rec, job.id)
        print(f"  matched {r['scored']} candidates for {job.title}")
    print(f"\nDone. Log in as {RECRUITER} / {PASSWORD} (recruiter) or {CANDIDATE} / {PASSWORD} (candidate).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="delete demo data first, then seed again")
    args = ap.parse_args()
    if not (ROOT / "sample_data/synthetic_candidates/manifest.json").exists():
        sys.exit("sample_data is empty. Run: python ../scripts/generate_synthetic_data.py")
    db = SessionLocal()
    try:
        if args.reset:
            reset(db)
        if db.scalar(select(User).where(User.email == RECRUITER)):
            print("Demo data already present - nothing to do. Use --reset to recreate it.")
            return
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
