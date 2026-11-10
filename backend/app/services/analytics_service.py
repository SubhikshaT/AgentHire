"""Recruiter analytics. Every number is a database query over the recruiter's own records."""
from collections import Counter
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.taxonomy import get_taxonomy
from app.database.base import utcnow
from app.models import (
    Application,
    AuditLog,
    CandidateMatch,
    CandidateSkill,
    Interview,
    Job,
    Resume,
    Skill,
    User,
)
from app.models.enums import InterviewStatus, JobStatus, ParsingStatus, Stage


def _apps(user: User):
    return select(Application.id).join(Job).where(Job.recruiter_id == user.id)


def overview(db: Session, user: User) -> dict:
    jobs = db.execute(select(Job.status, func.count()).where(Job.recruiter_id == user.id).group_by(Job.status)).all()
    by_status = {s: n for s, n in jobs}
    cand_ids = select(Application.candidate_id).join(Job).where(Job.recruiter_id == user.id)
    candidates = db.scalar(select(func.count(func.distinct(Application.candidate_id))).join(Job)
                           .where(Job.recruiter_id == user.id)) or 0
    resumes = db.execute(select(Resume.parsing_status, func.count()).where(Resume.candidate_id.in_(cand_ids))
                         .group_by(Resume.parsing_status)).all()
    rs = {s: n for s, n in resumes}
    ivs = db.execute(select(Interview.status, func.count()).where(Interview.application_id.in_(_apps(user)))
                     .group_by(Interview.status)).all()
    iv = {s: n for s, n in ivs}
    avg = db.scalar(select(func.avg(CandidateMatch.overall_score)).where(CandidateMatch.application_id.in_(_apps(user))))
    avg_iv = db.scalar(select(func.avg(Interview.total_score)).where(Interview.application_id.in_(_apps(user)),
                                                                      Interview.total_score.is_not(None)))
    return {
        "total_jobs": sum(by_status.values()), "active_jobs": by_status.get(JobStatus.PUBLISHED, 0),
        "draft_jobs": by_status.get(JobStatus.DRAFT, 0), "closed_jobs": by_status.get(JobStatus.CLOSED, 0),
        "total_candidates": candidates,
        "resumes_processed": rs.get(ParsingStatus.COMPLETED, 0), "resumes_failed": rs.get(ParsingStatus.FAILED, 0),
        "resumes_pending": rs.get(ParsingStatus.PENDING, 0) + rs.get(ParsingStatus.PROCESSING, 0),
        "interviews_completed": iv.get(InterviewStatus.COMPLETED, 0),
        "interviews_open": iv.get(InterviewStatus.READY, 0) + iv.get(InterviewStatus.IN_PROGRESS, 0),
        "average_match_score": round(avg, 1) if avg is not None else None,
        "average_interview_score": round(avg_iv, 1) if avg_iv is not None else None,
    }


def pipeline(db: Session, user: User) -> list[dict]:
    rows = dict(db.execute(select(Application.stage, func.count()).join(Job).where(Job.recruiter_id == user.id)
                           .group_by(Application.stage)).all())
    return [{"stage": s.value, "count": rows.get(s.value, 0)} for s in Stage]


def jobs(db: Session, user: User) -> list[dict]:
    rows = db.execute(
        select(Job.id, Job.title, Job.status, func.count(Application.id), func.avg(CandidateMatch.overall_score),
               func.max(CandidateMatch.overall_score))
        .outerjoin(Application, Application.job_id == Job.id)
        .outerjoin(CandidateMatch, CandidateMatch.application_id == Application.id)
        .where(Job.recruiter_id == user.id).group_by(Job.id).order_by(func.count(Application.id).desc())
    ).all()
    return [{"job_id": i, "title": t, "status": s, "applicants": n,
             "average_score": round(a, 1) if a is not None else None, "best_score": mx}
            for i, t, s, n, a, mx in rows]


def skills(db: Session, user: User, limit: int = 15) -> list[dict]:
    """Demand = how many of the recruiter's jobs require the skill; supply = applicants who have it."""
    tax = get_taxonomy()
    demand: Counter = Counter()
    for req, pref in db.execute(select(Job.required_skills, Job.preferred_skills).where(Job.recruiter_id == user.id)):
        for s in req or []:
            demand[tax.resolve(s) or s.lower()] += 1
        for s in pref or []:
            demand[tax.resolve(s) or s.lower()] += 0.5
    cand_ids = select(Application.candidate_id).join(Job).where(Job.recruiter_id == user.id).distinct()
    supply = dict(db.execute(select(Skill.normalized_name, func.count(func.distinct(CandidateSkill.candidate_id)))
                             .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
                             .where(CandidateSkill.candidate_id.in_(cand_ids)).group_by(Skill.normalized_name)).all())
    out = [{"skill": tax.display(k), "key": k, "demand": v, "candidates_with_skill": supply.get(k, 0)}
           for k, v in demand.most_common(limit)]
    return out


def interviews(db: Session, user: User, weeks: int = 8) -> list[dict]:
    since = utcnow() - timedelta(weeks=weeks)
    rows = db.execute(select(Interview.completed_at, Interview.total_score)
                      .where(Interview.application_id.in_(_apps(user)), Interview.status == InterviewStatus.COMPLETED,
                             Interview.completed_at >= since)).all()
    buckets: dict[str, list] = {}
    for done, score in rows:
        start = (done - timedelta(days=done.weekday())).date().isoformat()
        buckets.setdefault(start, []).append(score)
    out = []
    for wk in sorted(buckets):
        scores = [s for s in buckets[wk] if s is not None]
        out.append({"week_start": wk, "completed": len(buckets[wk]),
                    "average_score": round(sum(scores) / len(scores), 1) if scores else None})
    return out


def recent_activity(db: Session, user: User, limit: int = 12) -> list[dict]:
    rows = db.execute(select(AuditLog).where(AuditLog.user_id == user.id)
                      .order_by(AuditLog.created_at.desc()).limit(limit)).scalars().all()
    return [{"action": r.action, "entity_type": r.entity_type, "entity_id": r.entity_id, "meta": r.meta,
             "created_at": r.created_at} for r in rows]
