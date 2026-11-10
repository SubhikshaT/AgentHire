import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_recruiter
from app.database.session import get_db
from app.models import User
from app.models.enums import JobStatus
from app.schemas.common import Page
from app.schemas.job import JobAnalyzeRequest, JobCreate, JobOut, JobUpdate
from app.services import job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _out(job, count: int) -> JobOut:
    o = JobOut.model_validate(job)
    o.applicant_count = count
    return o


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(data: JobCreate, user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    return _out(job_service.create_job(db, user, data), 0)


@router.get("", response_model=Page[JobOut])
def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=100),
    status_: JobStatus | None = Query(None, alias="status"),
    sort: str = Query("-created_at"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows, total = job_service.list_jobs(db, user, page, page_size, q, status_.value if status_ else None, sort)
    return Page(items=[_out(j, n) for j, n in rows], total=total, page=page, page_size=page_size)


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = job_service.get_job_for_user(db, user, job_id)
    count = job_service.applicant_count(db, job.id) if user.role == "recruiter" else 0
    return _out(job, count)


@router.put("/{job_id}", response_model=JobOut)
def update_job(job_id: uuid.UUID, data: JobUpdate, user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    job = job_service.update_job(db, user, job_id, data)
    return _out(job, job_service.applicant_count(db, job.id))


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_job(job_id: uuid.UUID, user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    job_service.delete_job(db, user, job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{job_id}/publish", response_model=JobOut)
def publish(job_id: uuid.UUID, user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    job = job_service.set_status(db, user, job_id, JobStatus.PUBLISHED)
    return _out(job, job_service.applicant_count(db, job.id))


@router.post("/{job_id}/unpublish", response_model=JobOut)
def unpublish(job_id: uuid.UUID, user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    job = job_service.set_status(db, user, job_id, JobStatus.DRAFT)
    return _out(job, job_service.applicant_count(db, job.id))


@router.post("/{job_id}/close", response_model=JobOut)
def close(job_id: uuid.UUID, user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    job = job_service.set_status(db, user, job_id, JobStatus.CLOSED)
    return _out(job, job_service.applicant_count(db, job.id))


@router.post("/{job_id}/analyze")
def analyze(job_id: uuid.UUID, data: JobAnalyzeRequest, user: User = Depends(require_recruiter),
            db: Session = Depends(get_db)):
    """Extract structured requirements from the description. With apply=true they are saved to the job."""
    return job_service.analyze_job(db, user, job_id, data.description, data.apply).model_dump()


@router.post("/analyze-text")
def analyze_text(data: JobAnalyzeRequest, user: User = Depends(require_recruiter)):
    """Analyze a pasted description before the job exists (used by the create form)."""
    from app.ai.agents.job_agent import JobAnalysisAgent

    return JobAnalysisAgent().analyze(data.description or "").model_dump()
