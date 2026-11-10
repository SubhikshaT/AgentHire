"""AI audit viewer: every AI output with provider, model, versions, timing and validation result."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_recruiter
from app.database.session import get_db
from app.models import AIAuditLog, Application, Interview, InterviewAnswer, InterviewQuestion, Job, User

router = APIRouter(prefix="/ai-audit", tags=["ai-audit"])


@router.get("")
def list_audit(page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=100),
               user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    """AI records that belong to this recruiter's interviews (generation, follow-ups, evaluations)."""
    my_iv = select(Interview.id).join(Application, Application.id == Interview.application_id) \
        .join(Job, Job.id == Application.job_id).where(Job.recruiter_id == user.id)
    my_q = select(InterviewQuestion.id).where(InterviewQuestion.interview_id.in_(my_iv))
    my_a = select(InterviewAnswer.id).where(InterviewAnswer.question_id.in_(my_q))
    as_text = lambda sub, col: select(cast(col, String)).where(col.in_(sub))  # noqa: E731
    cond = or_(
        AIAuditLog.input_refs["interview_id"].astext.in_(as_text(my_iv, Interview.id)),
        AIAuditLog.input_refs["question_id"].astext.in_(as_text(my_q, InterviewQuestion.id)),
        AIAuditLog.input_refs["answer_id"].astext.in_(as_text(my_a, InterviewAnswer.id)),
    )
    stmt = select(AIAuditLog).where(cond)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(AIAuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    items = [{"id": r.id, "agent": r.agent, "provider": r.provider, "model_id": r.model_id,
              "prompt_version": r.prompt_version, "rubric_version": r.rubric_version, "input_refs": r.input_refs,
              "output_ref_type": r.output_ref_type, "output_ref_id": r.output_ref_id, "duration_ms": r.duration_ms,
              "validation_passed": r.validation_passed, "retry_count": r.retry_count,
              "error_message": r.error_message, "human_edited": r.human_edited, "created_at": r.created_at}
             for r in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size}
