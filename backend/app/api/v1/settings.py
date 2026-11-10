from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.agents.matching_agent import DEFAULT_WEIGHTS
from app.ai.providers import llm_status
from app.ai.rubric import DEFAULT_RUBRIC_WEIGHTS, DIMENSION_DESCRIPTIONS, RUBRIC_VERSION
from app.api.deps import get_current_user, require_recruiter
from app.core.config import get_settings
from app.database.session import get_db
from app.models import User
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


class Weights(BaseModel):
    weights: dict[str, float]


@router.get("")
def get_all(user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    return {
        "matching_weights": settings_service.matching_weights(db, user.id),
        "rubric_weights": settings_service.rubric_weights(db, user.id),
        "default_matching_weights": DEFAULT_WEIGHTS,
        "default_rubric_weights": DEFAULT_RUBRIC_WEIGHTS,
        "rubric_dimensions": DIMENSION_DESCRIPTIONS,
        "rubric_version": RUBRIC_VERSION,
    }


@router.put("/weights")
def put_weights(data: Weights, user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    return {"matching_weights": settings_service.set_matching_weights(db, user, data.weights)}


@router.put("/rubric")
def put_rubric(data: Weights, user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    return {"rubric_weights": settings_service.set_rubric_weights(db, user, data.weights)}


@router.get("/llm-status")
def get_llm_status(user: User = Depends(get_current_user)):
    """Which AI provider is configured and whether it answers. Never returns keys."""
    s = get_settings()
    return {**llm_status(), "vector_backend": s.vector_backend, "embedding_model": s.embedding_model}
