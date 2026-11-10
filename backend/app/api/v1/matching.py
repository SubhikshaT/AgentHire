import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_recruiter
from app.database.session import get_db
from app.models import User
from app.services import matching_service

router = APIRouter(prefix="/matching", tags=["matching"])


class CompareRequest(BaseModel):
    job_id: uuid.UUID
    candidate_ids: list[uuid.UUID] = Field(min_length=2, max_length=4)


@router.post("/jobs/{job_id}/run")
def run(job_id: uuid.UUID, user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    return matching_service.run_for_job(db, user, job_id)


@router.get("/jobs/{job_id}/results")
def results(job_id: uuid.UUID, user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    return matching_service.results_for_job(db, user, job_id)


@router.post("/compare")
def compare(data: CompareRequest, user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    return matching_service.compare(db, user, data.job_id, data.candidate_ids)


@router.get("/{match_id}")
def get_match(match_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Recruiters see matches for their jobs; candidates see their own (skill-gap view)."""
    return matching_service.get_match(db, user, match_id)
