"""Ownership checks. Every service that loads a record by id goes through these.

Missing and not-allowed both return 404 so ids of other users' records are not revealed.
"""
import uuid

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import Application, CandidateProfile, Job, Resume, User
from app.models.enums import Role


def get_own_job(db: Session, user: User, job_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.recruiter_id != user.id:
        raise NotFoundError("Job not found.")
    return job


def candidate_profile_of(db: Session, user: User) -> CandidateProfile | None:
    return db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))


def recruiter_can_see_candidate(db: Session, recruiter: User, candidate_id: uuid.UUID) -> bool:
    return bool(
        db.scalar(
            select(
                exists().where(
                    Application.candidate_id == candidate_id,
                    Application.job_id == Job.id,
                    Job.recruiter_id == recruiter.id,
                )
            )
        )
    )


def get_visible_candidate(db: Session, user: User, candidate_id: uuid.UUID) -> CandidateProfile:
    cand = db.get(CandidateProfile, candidate_id)
    if cand is None:
        raise NotFoundError("Candidate not found.")
    if user.role == Role.CANDIDATE:
        if cand.user_id != user.id:
            raise NotFoundError("Candidate not found.")
    elif not recruiter_can_see_candidate(db, user, candidate_id):
        raise NotFoundError("Candidate not found.")
    return cand


def get_visible_application(db: Session, user: User, application_id: uuid.UUID) -> Application:
    app = db.get(Application, application_id)
    if app is None:
        raise NotFoundError("Application not found.")
    if user.role == Role.RECRUITER:
        if app.job.recruiter_id != user.id:
            raise NotFoundError("Application not found.")
    else:
        profile = candidate_profile_of(db, user)
        if profile is None or app.candidate_id != profile.id:
            raise NotFoundError("Application not found.")
    return app


def get_visible_resume(db: Session, user: User, resume_id: uuid.UUID) -> Resume:
    r = db.get(Resume, resume_id)
    if r is None:
        raise NotFoundError("Resume not found.")
    if user.role == Role.CANDIDATE:
        profile = candidate_profile_of(db, user)
        if profile is None or r.candidate_id != profile.id:
            raise NotFoundError("Resume not found.")
    else:
        ok = r.uploaded_by == user.id or (r.candidate_id and recruiter_can_see_candidate(db, user, r.candidate_id))
        if not ok:
            raise NotFoundError("Resume not found.")
    return r
