import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.agents.learning_agent import all_resource_keys
from app.api.deps import get_current_user, require_candidate
from app.core.exceptions import AppError, NotFoundError
from app.database.session import get_db
from app.models import CandidateMatch, LearningProgress, User
from app.services import skill_graph_service
from app.services.permissions import candidate_profile_of, get_visible_application
from app.services.report_service import learning_for_match

router = APIRouter(tags=["learning"])


class ProgressIn(BaseModel):
    resource_key: str = Field(min_length=1, max_length=120)
    completed: bool = True


@router.get("/learning/recommendations")
def recommendations(application_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = get_visible_application(db, user, application_id)
    match = db.scalar(select(CandidateMatch).where(CandidateMatch.application_id == app.id))
    recs = learning_for_match(match)
    done = set(db.scalars(select(LearningProgress.resource_key)
                          .where(LearningProgress.candidate_id == app.candidate_id)).all())
    for r in recs:
        r["completed"] = r["key"] in done
    return {"application_id": app.id, "job_title": app.job.title, "matched": match is not None, "items": recs}


@router.post("/learning/progress")
def progress(data: ProgressIn, user: User = Depends(require_candidate), db: Session = Depends(get_db)):
    if data.resource_key not in all_resource_keys():
        raise AppError("Unknown learning resource.", code="unknown_resource", status_code=404)
    profile = candidate_profile_of(db, user)
    if profile is None:
        raise NotFoundError("Profile not found.")
    row = db.scalar(select(LearningProgress).where(LearningProgress.candidate_id == profile.id,
                                                   LearningProgress.resource_key == data.resource_key))
    if data.completed and row is None:
        db.add(LearningProgress(candidate_id=profile.id, resource_key=data.resource_key))
    elif not data.completed and row is not None:
        db.delete(row)
    db.commit()
    return {"resource_key": data.resource_key, "completed": data.completed}


@router.get("/candidates/{candidate_id}/skill-graph")
def skill_graph(candidate_id: uuid.UUID, job_id: uuid.UUID, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return skill_graph_service.build(db, user, candidate_id, job_id)
