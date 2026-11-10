from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_recruiter
from app.database.session import get_db
from app.models import User
from app.services import analytics_service as a

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def overview(user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    return {**a.overview(db, user), "recent_activity": a.recent_activity(db, user)}


@router.get("/jobs")
def jobs(user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    return a.jobs(db, user)


@router.get("/pipeline")
def pipeline(user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    return a.pipeline(db, user)


@router.get("/skills")
def skills(user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    return a.skills(db, user)


@router.get("/interviews")
def interviews(user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    return a.interviews(db, user)
