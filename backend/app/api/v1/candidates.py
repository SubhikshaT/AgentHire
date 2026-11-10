import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_candidate, require_recruiter
from app.core.exceptions import NotFoundError
from app.database.session import get_db
from app.models import User
from app.models.enums import Stage
from app.schemas.candidate import CandidateListItem, CandidateOut, CandidateSkillOut, CandidateUpdate, SkillsUpdate
from app.schemas.common import Page
from app.services import candidate_service
from app.services.permissions import candidate_profile_of, get_visible_candidate

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=Page[CandidateListItem])
def list_candidates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=100),
    job_id: uuid.UUID | None = None,
    stage: Stage | None = None,
    skill: str | None = Query(None, max_length=80),
    min_experience: float | None = Query(None, ge=0, le=60),
    sort: str = Query("-created_at", pattern="^(-?created_at|name|-?experience|-score)$"),
    user: User = Depends(require_recruiter),
    db: Session = Depends(get_db),
):
    items, total = candidate_service.list_for_recruiter(
        db, user, page=page, page_size=page_size, q=q, job_id=job_id, stage=stage.value if stage else None,
        skill=skill, min_experience=min_experience, sort=sort)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/me", response_model=CandidateOut)
def my_profile(user: User = Depends(require_candidate), db: Session = Depends(get_db)):
    profile = candidate_profile_of(db, user)
    if profile is None:
        raise NotFoundError("Profile not found.")
    return candidate_service.detail(db, user, profile)


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(candidate_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return candidate_service.detail(db, user, get_visible_candidate(db, user, candidate_id))


@router.put("/{candidate_id}", response_model=CandidateOut)
def update_candidate(candidate_id: uuid.UUID, data: CandidateUpdate, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    profile = candidate_service.update_profile(db, user, candidate_id, data)
    return candidate_service.detail(db, user, profile)


@router.get("/{candidate_id}/skills", response_model=list[CandidateSkillOut])
def get_skills(candidate_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return candidate_service.skills_out(get_visible_candidate(db, user, candidate_id))


@router.put("/{candidate_id}/skills", response_model=list[CandidateSkillOut])
def put_skills(candidate_id: uuid.UUID, data: SkillsUpdate, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    return candidate_service.skills_out(candidate_service.replace_skills(db, user, candidate_id, data))


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_candidate(candidate_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    candidate_service.delete_candidate(db, user, candidate_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
