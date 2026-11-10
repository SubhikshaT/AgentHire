"""Candidate evaluation reports: built only from stored results, plus recruiter notes and PDF export."""
import uuid
from pathlib import Path

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.ai.agents.learning_agent import VERSION as LEARN_VERSION, recommend
from app.ai.agents.matching_agent import DEFAULT_WEIGHTS
from app.ai.rubric import RUBRIC_VERSION
from app.core.config import BACKEND_DIR
from app.core.exceptions import AppError, NotFoundError
from app.database.base import utcnow
from app.models import (
    Application,
    CandidateMatch,
    EvaluationReport,
    Interview,
    Job,
    RecruiterNote,
    User,
)
from app.models.enums import InterviewStatus, InterviewType
from app.services.audit_service import log_action
from app.services.interview_service import interview_out
from app.services.matching_service import METHOD_VERSION
from app.services.permissions import get_visible_application

METHODOLOGY_VERSION = f"report-1.0|{METHOD_VERSION}|{RUBRIC_VERSION}"  # fits VARCHAR(40)
REPORT_DIR = BACKEND_DIR / "storage" / "reports"

LIMITATIONS = [
    "The match score shows how well resume evidence covers the job requirements. It is not a probability of "
    "being hired or of job success.",
    "Resume parsing is rule-based and can miss or misread information; fields marked auto-extracted should be "
    "checked against the original resume.",
    "Interview scores rate written answers only, against a fixed rubric. They do not measure intelligence, "
    "personality or honesty.",
    "Protected characteristics (gender, age, religion, ethnicity, disability, photos) are not used anywhere in scoring.",
    "This report is decision support. A person makes the hiring decision.",
]


def learning_for_match(match: CandidateMatch | None) -> list[dict]:
    if not match:
        return []
    ex = match.explanation or {}
    gaps = [(s, "required") for s in ex.get("required_skills", {}).get("missing", [])]
    gaps += [(r["skill"], "related") for r in ex.get("required_skills", {}).get("related", [])]
    gaps += [(s, "preferred") for s in ex.get("preferred_skills", {}).get("missing", [])]
    return recommend(gaps)


def generate(db: Session, user: User, application_id: uuid.UUID, interview_id: uuid.UUID | None) -> EvaluationReport:
    app = get_visible_application(db, user, application_id)
    if app.job.recruiter_id != user.id:
        raise NotFoundError("Application not found.")
    match = db.scalar(select(CandidateMatch).where(CandidateMatch.application_id == app.id))
    if interview_id:
        iv = db.get(Interview, interview_id)
        if iv is None or iv.application_id != app.id:
            raise NotFoundError("Interview not found for this application.")
    else:
        iv = db.scalar(select(Interview).where(Interview.application_id == app.id,
                                               Interview.status == InterviewStatus.COMPLETED,
                                               Interview.interview_type == InterviewType.ASSIGNED)
                       .order_by(Interview.completed_at.desc()).limit(1))
    if match is None and iv is None:
        raise AppError("Run matching or complete an interview before generating a report.", code="nothing_to_report")
    c = app.candidate
    interview = interview_out(db, user, iv) if iv else None
    if interview:
        answers = [q.get("answer") for q in interview["questions"] if q.get("answer")]
        verdicts: dict[str, int] = {}
        for a in answers:
            if a.get("verdict"):
                verdicts[a["verdict"]] = verdicts.get(a["verdict"], 0) + 1
        interview["summary"] = {
            "answered": sum(1 for a in answers if a.get("text")),
            "evaluated": sum(1 for a in answers if a.get("evaluation_status") == "evaluated"),
            "pending": sum(1 for a in answers if a.get("evaluation_status") in ("pending_llm", "failed")),
            "verdicts": verdicts,
        }
    data = {
        "candidate": {
            "id": str(c.id), "name": c.full_name, "email": c.email, "is_synthetic": c.is_synthetic,
            "total_experience_years": c.total_experience_years,
            "education": c.education or [], "certifications": c.certifications or [],
            "skills": [{"name": cs.skill.name, "section": cs.evidence_section, "status": cs.verification_status}
                       for cs in c.skills],
            "work_experience": [{"title": e.get("title"), "company": e.get("company"), "start": e.get("start"),
                                 "end": e.get("end")} for e in (c.work_experience or [])],
            "projects": [{"name": p.get("name"), "skills": p.get("skills", [])} for p in (c.projects or [])],
            "field_verification": c.field_verification or {},
        },
        "job": {"id": str(app.job.id), "title": app.job.title, "required_skills": app.job.required_skills,
                "preferred_skills": app.job.preferred_skills, "minimum_experience": app.job.minimum_experience},
        "stage": app.stage,
        "match": None if match is None else {
            "overall_score": match.overall_score, "keyword_baseline_score": match.keyword_baseline_score,
            "weights_used": match.weights_used or DEFAULT_WEIGHTS, "explanation": match.explanation,
            "calculated_at": match.calculated_at.isoformat(),
        },
        "interview": interview and {k: interview[k] for k in
                                    ("id", "status", "difficulty", "total_score", "completed_at", "questions",
                                     "summary", "rubric_version")},
        "learning_recommendations": learning_for_match(match),
        "limitations": LIMITATIONS,
        "versions": {"report": "report-1.0", "matching": METHOD_VERSION, "rubric": RUBRIC_VERSION,
                     "learning": LEARN_VERSION},
        "generated_by": user.name,
    }
    rep = EvaluationReport(application_id=app.id, interview_id=iv.id if iv else None,
                           report_data=_jsonable(data), methodology_version=METHODOLOGY_VERSION,
                           generated_by=user.id, generated_at=utcnow())
    db.add(rep)
    db.flush()
    log_action(db, user.id, "report.generated", "evaluation_report", rep.id)
    db.commit()
    return rep


def _jsonable(x):
    import json

    return json.loads(json.dumps(x, default=str))


def get_report(db: Session, user: User, report_id: uuid.UUID) -> EvaluationReport:
    rep = db.get(EvaluationReport, report_id)
    if rep is None:
        raise NotFoundError("Report not found.")
    app = db.get(Application, rep.application_id)
    if app is None or app.job.recruiter_id != user.id:
        raise NotFoundError("Report not found.")
    return rep


def report_out(rep: EvaluationReport, db: Session) -> dict:
    notes = db.execute(select(RecruiterNote, User.name).outerjoin(User, User.id == RecruiterNote.recruiter_id)
                       .where(RecruiterNote.report_id == rep.id).order_by(RecruiterNote.created_at)).all()
    return {"id": rep.id, "application_id": rep.application_id, "interview_id": rep.interview_id,
            "methodology_version": rep.methodology_version, "generated_at": rep.generated_at,
            "report_data": rep.report_data,
            "notes": [{"id": n.id, "text": n.note_text, "author": name, "created_at": n.created_at,
                       "label": "Recruiter comment"} for n, name in notes]}


def list_reports(db: Session, user: User, q: str | None, job_id: uuid.UUID | None, page: int, page_size: int):
    stmt = (select(EvaluationReport, Application, Job)
            .join(Application, Application.id == EvaluationReport.application_id)
            .join(Job, Job.id == Application.job_id).where(Job.recruiter_id == user.id))
    if job_id:
        stmt = stmt.where(Job.id == job_id)
    if q:
        like = f"%{q.strip()}%"
        from app.models import CandidateProfile
        stmt = stmt.join(CandidateProfile, CandidateProfile.id == Application.candidate_id).where(
            or_(CandidateProfile.full_name.ilike(like), Job.title.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.order_by(EvaluationReport.generated_at.desc())
                      .offset((page - 1) * page_size).limit(page_size)).all()
    items = [{"id": r.id, "application_id": a.id, "job_id": j.id, "job_title": j.title,
              "candidate_name": a.candidate.full_name, "is_synthetic": a.candidate.is_synthetic,
              "overall_score": (r.report_data.get("match") or {}).get("overall_score"),
              "interview_score": (r.report_data.get("interview") or {}).get("total_score"),
              "has_interview": r.interview_id is not None, "generated_at": r.generated_at,
              "methodology_version": r.methodology_version} for r, a, j in rows]
    return items, total


def add_note(db: Session, user: User, report_id: uuid.UUID, text: str) -> dict:
    rep = get_report(db, user, report_id)
    db.add(RecruiterNote(report_id=rep.id, recruiter_id=user.id, note_text=text.strip()))
    rep.report_file_path = None  # PDF must be rebuilt to include the note
    log_action(db, user.id, "report.note_added", "evaluation_report", rep.id)
    db.commit()
    return report_out(rep, db)


def pdf_path(db: Session, user: User, report_id: uuid.UUID) -> Path:
    from app.services.pdf_service import build_report_pdf

    rep = get_report(db, user, report_id)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"{rep.id}.pdf"
    if rep.report_file_path is None or not path.exists():
        build_report_pdf(report_out(rep, db), path)
        rep.report_file_path = str(path.relative_to(BACKEND_DIR))
        log_action(db, user.id, "report.pdf_built", "evaluation_report", rep.id)
        db.commit()
    return path
