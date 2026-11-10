"""Applications and the recruitment pipeline."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models import Application, CandidateMatch, CandidateProfile, Job, Resume, StageHistory, User
from app.models.enums import ApplicationSource, JobStatus, ParsingStatus, Stage
from app.services.audit_service import log_action
from app.services.permissions import candidate_profile_of, get_own_job, get_visible_application
from app.utils.files import resolve_stored


def to_out(db: Session, app: Application) -> dict:
    match = db.scalar(select(CandidateMatch).where(CandidateMatch.application_id == app.id))
    latest = db.scalar(select(Resume.parsing_status).where(Resume.candidate_id == app.candidate_id)
                       .order_by(Resume.uploaded_at.desc()).limit(1))
    c = app.candidate
    return {
        "id": app.id, "candidate_id": app.candidate_id, "job_id": app.job_id, "job_title": app.job.title,
        "candidate_name": c.full_name, "candidate_email": c.email, "stage": app.stage, "source": app.source,
        "created_at": app.created_at, "overall_score": match.overall_score if match else None,
        "match_id": match.id if match else None, "resume_status": latest, "is_synthetic": c.is_synthetic,
    }


def apply(db: Session, user: User, job_id: uuid.UUID) -> Application:
    job = db.get(Job, job_id)
    if job is None or job.status != JobStatus.PUBLISHED:
        raise NotFoundError("Job not found or not open for applications.")
    profile = candidate_profile_of(db, user)
    if profile is None:
        raise AppError("Create your profile first.", code="no_profile")
    has_resume = db.scalar(select(func.count(Resume.id)).where(
        Resume.candidate_id == profile.id, Resume.parsing_status == ParsingStatus.COMPLETED))
    if not has_resume:
        raise AppError("Upload your resume (and wait for it to be processed) before applying.", code="resume_required")
    if db.scalar(select(Application).where(Application.candidate_id == profile.id, Application.job_id == job_id)):
        raise ConflictError("You have already applied to this job.", code="already_applied")
    app = Application(candidate_id=profile.id, job_id=job_id, stage=Stage.APPLIED, source=ApplicationSource.CANDIDATE_APPLIED)
    db.add(app)
    db.flush()
    db.add(StageHistory(application_id=app.id, from_stage=None, to_stage=Stage.APPLIED, changed_by=user.id, note="Applied"))
    log_action(db, user.id, "application.created", "application", app.id, {"job_id": str(job_id)})
    db.commit()
    return app


def list_for_job(db: Session, user: User, job_id: uuid.UUID, stage: str | None) -> list[dict]:
    get_own_job(db, user, job_id)
    stmt = select(Application).where(Application.job_id == job_id)
    if stage:
        stmt = stmt.where(Application.stage == stage)
    apps = db.scalars(stmt.order_by(Application.created_at.desc())).all()
    out = [to_out(db, a) for a in apps]
    out.sort(key=lambda a: (a["overall_score"] is None, -(a["overall_score"] or 0)))
    return out


def list_mine(db: Session, user: User) -> list[dict]:
    profile = candidate_profile_of(db, user)
    if profile is None:
        return []
    apps = db.scalars(select(Application).where(Application.candidate_id == profile.id)
                      .order_by(Application.created_at.desc())).all()
    return [to_out(db, a) for a in apps]


def change_stage(db: Session, user: User, application_id: uuid.UUID, stage: Stage, note: str | None) -> Application:
    app = get_visible_application(db, user, application_id)
    if app.stage == stage:
        raise AppError("The candidate is already in this stage.", code="same_stage")
    db.add(StageHistory(application_id=app.id, from_stage=app.stage, to_stage=stage, changed_by=user.id,
                        note=(note or "").strip() or None))
    log_action(db, user.id, "application.stage_changed", "application", app.id, {"from": app.stage, "to": stage.value})
    app.stage = stage
    db.commit()
    return app


def history(db: Session, user: User, application_id: uuid.UUID) -> list[dict]:
    app = get_visible_application(db, user, application_id)
    rows = db.execute(
        select(StageHistory, User.name).outerjoin(User, User.id == StageHistory.changed_by)
        .where(StageHistory.application_id == app.id).order_by(StageHistory.changed_at)
    ).all()
    return [{"id": h.id, "from_stage": h.from_stage, "to_stage": h.to_stage, "changed_by": h.changed_by,
             "changed_by_name": n, "changed_at": h.changed_at, "note": h.note} for h, n in rows]


def withdraw_from_job(db: Session, user: User, application_id: uuid.UUID) -> None:
    """Recruiter removes a candidate from one of their jobs (no data is deleted for other jobs)."""
    app = get_visible_application(db, user, application_id)
    log_action(db, user.id, "application.removed", "application", app.id)
    candidate_id = app.candidate_id
    db.delete(app)
    db.flush()
    # delete recruiter-imported placeholder profiles that no longer belong to any job
    profile = db.get(CandidateProfile, candidate_id)
    remaining = db.scalar(select(func.count(Application.id)).where(Application.candidate_id == candidate_id))
    paths: list[str] = []
    if profile is not None and profile.user_id is None and not remaining:
        paths = [r.stored_path for r in db.scalars(select(Resume).where(Resume.candidate_id == candidate_id)).all()]
        db.delete(profile)
    db.commit()
    for p in paths:
        try:
            resolve_stored(p).unlink(missing_ok=True)
        except Exception:
            pass
