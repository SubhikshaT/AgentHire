"""Job CRUD, publishing and analysis."""
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.ai.agents.job_agent import JobAnalysis, JobAnalysisAgent
from app.core.exceptions import AppError, NotFoundError
from app.models import Application, Job, User
from app.models.enums import JobStatus, Role
from app.schemas.job import JobCreate, JobUpdate
from app.services.audit_service import log_action
from app.services.permissions import get_own_job

STRUCTURED_FIELDS = [
    "required_skills", "preferred_skills", "soft_skills", "minimum_experience",
    "education_requirements", "certifications", "responsibilities",
]


def job_text_for_embedding(job: Job) -> str:
    """Text used for the job's semantic embedding: title + requirements + responsibilities."""
    parts = [job.title]
    if job.required_skills:
        parts.append("Required skills: " + ", ".join(job.required_skills))
    if job.preferred_skills:
        parts.append("Preferred skills: " + ", ".join(job.preferred_skills))
    if job.responsibilities:
        parts.append("Responsibilities: " + "; ".join(job.responsibilities))
    if job.minimum_experience:
        parts.append(f"Experience: {job.minimum_experience:g}+ years")
    if not job.required_skills and not job.responsibilities and job.description:
        parts.append(job.description[:2000])
    return "\n".join(parts)


def invalidate_embedding(job: Job) -> None:
    job.embedding = None
    job.embedding_model = None


def apply_analysis(job: Job, a: JobAnalysis, only_empty: bool) -> None:
    for f in STRUCTURED_FIELDS:
        val = getattr(a, f)
        cur = getattr(job, f)
        if only_empty and cur not in (None, [], 0):
            continue
        if val not in (None, []):
            setattr(job, f, val)
    if a.department and (not only_empty or not job.department):
        job.department = a.department


def create_job(db: Session, user: User, data: JobCreate) -> Job:
    job = Job(
        recruiter_id=user.id,
        **data.model_dump(exclude={"analyze", "education_requirements"}),
        education_requirements=[e.model_dump() for e in data.education_requirements],
        status=JobStatus.DRAFT,
    )
    if data.analyze and data.description.strip():
        a = JobAnalysisAgent().analyze(data.description, data.title)
        apply_analysis(job, a, only_empty=True)
        job.analysis_metadata = {"method": a.method, "agent_version": JobAnalysisAgent.version}
    db.add(job)
    db.flush()
    log_action(db, user.id, "job.created", "job", job.id)
    db.commit()
    return job


def update_job(db: Session, user: User, job_id: uuid.UUID, data: JobUpdate) -> Job:
    job = get_own_job(db, user, job_id)
    for k, v in data.model_dump(exclude={"education_requirements"}).items():
        setattr(job, k, v)
    job.education_requirements = [e.model_dump() for e in data.education_requirements]
    meta = dict(job.analysis_metadata or {})
    meta["manually_edited"] = True
    job.analysis_metadata = meta
    invalidate_embedding(job)
    log_action(db, user.id, "job.updated", "job", job.id)
    db.commit()
    return job


def delete_job(db: Session, user: User, job_id: uuid.UUID) -> None:
    job = get_own_job(db, user, job_id)
    log_action(db, user.id, "job.deleted", "job", job.id, {"title": job.title})
    db.delete(job)
    db.commit()


def set_status(db: Session, user: User, job_id: uuid.UUID, status: JobStatus) -> Job:
    job = get_own_job(db, user, job_id)
    if status == JobStatus.PUBLISHED and not job.required_skills:
        raise AppError("Add at least one required skill before publishing.", code="missing_required_skills")
    job.status = status
    log_action(db, user.id, f"job.{status.value}", "job", job.id)
    db.commit()
    return job


def analyze_job(db: Session, user: User, job_id: uuid.UUID, description: str | None, apply: bool) -> JobAnalysis:
    job = get_own_job(db, user, job_id)
    text = description if description is not None else job.description
    if not text or not text.strip():
        raise AppError("The job has no description to analyze.", code="empty_description")
    a = JobAnalysisAgent().analyze(text, job.title)
    if apply:
        if description is not None:
            job.description = description
        apply_analysis(job, a, only_empty=False)
        job.analysis_metadata = {"method": a.method, "agent_version": JobAnalysisAgent.version, "manually_edited": False}
        invalidate_embedding(job)
        log_action(db, user.id, "job.analyzed", "job", job.id)
        db.commit()
    return a


def list_jobs(db: Session, user: User, page: int, page_size: int, q: str | None, status: str | None,
              sort: str = "-created_at") -> tuple[list[tuple[Job, int]], int]:
    count_sq = (
        select(Application.job_id, func.count(Application.id).label("n")).group_by(Application.job_id).subquery()
    )
    stmt = select(Job, func.coalesce(count_sq.c.n, 0)).outerjoin(count_sq, count_sq.c.job_id == Job.id)
    if user.role == Role.RECRUITER:
        stmt = stmt.where(Job.recruiter_id == user.id)
        if status:
            stmt = stmt.where(Job.status == status)
    else:
        stmt = stmt.where(Job.status == JobStatus.PUBLISHED)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Job.title.ilike(like), Job.department.ilike(like), Job.description.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    order = {
        "-created_at": Job.created_at.desc(), "created_at": Job.created_at.asc(),
        "title": Job.title.asc(), "-title": Job.title.desc(),
        "-applicants": func.coalesce(count_sq.c.n, 0).desc(),
    }.get(sort, Job.created_at.desc())
    rows = db.execute(stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)).all()
    return [(j, n) for j, n in rows], total or 0


def get_job_for_user(db: Session, user: User, job_id: uuid.UUID) -> Job:
    if user.role == Role.RECRUITER:
        return get_own_job(db, user, job_id)
    job = db.get(Job, job_id)
    if job is None or job.status != JobStatus.PUBLISHED:
        raise NotFoundError("Job not found.")
    return job


def applicant_count(db: Session, job_id: uuid.UUID) -> int:
    return db.scalar(select(func.count(Application.id)).where(Application.job_id == job_id)) or 0
