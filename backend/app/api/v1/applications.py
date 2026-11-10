import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_candidate, require_recruiter
from app.database.session import get_db
from app.models import User
from app.models.enums import Stage
from app.schemas.application import ApplicationOut, StageChange, StageHistoryOut
from app.services import application_service as svc

router = APIRouter(tags=["applications"])


@router.post("/jobs/{job_id}/apply", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def apply(job_id: uuid.UUID, user: User = Depends(require_candidate), db: Session = Depends(get_db)):
    return svc.to_out(db, svc.apply(db, user, job_id))


@router.get("/jobs/{job_id}/applications", response_model=list[ApplicationOut])
def job_applications(job_id: uuid.UUID, stage: Stage | None = None, user: User = Depends(require_recruiter),
                     db: Session = Depends(get_db)):
    return svc.list_for_job(db, user, job_id, stage.value if stage else None)


@router.get("/applications/me", response_model=list[ApplicationOut])
def my_applications(user: User = Depends(require_candidate), db: Session = Depends(get_db)):
    return svc.list_mine(db, user)


@router.patch("/applications/{application_id}/stage", response_model=ApplicationOut)
def change_stage(application_id: uuid.UUID, data: StageChange, user: User = Depends(require_recruiter),
                 db: Session = Depends(get_db)):
    return svc.to_out(db, svc.change_stage(db, user, application_id, data.stage, data.note))


@router.get("/applications/{application_id}/history", response_model=list[StageHistoryOut])
def stage_history(application_id: uuid.UUID, user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    return svc.history(db, user, application_id)


@router.delete("/applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def remove(application_id: uuid.UUID, user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    svc.withdraw_from_job(db, user, application_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
