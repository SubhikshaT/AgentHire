import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_recruiter
from app.database.session import get_db
from app.models import User
from app.schemas.common import Page
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


class GenerateReport(BaseModel):
    application_id: uuid.UUID
    interview_id: uuid.UUID | None = None


class NoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=3000)


@router.get("", response_model=Page[dict])
def list_reports(q: str | None = Query(None, max_length=100), job_id: uuid.UUID | None = None,
                 page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                 user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    items, total = report_service.list_reports(db, user, q, job_id, page, page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("/generate", status_code=201)
def generate(data: GenerateReport, user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    rep = report_service.generate(db, user, data.application_id, data.interview_id)
    return report_service.report_out(rep, db)


@router.get("/{report_id}")
def get_report(report_id: uuid.UUID, user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    return report_service.report_out(report_service.get_report(db, user, report_id), db)


@router.post("/{report_id}/notes")
def add_note(report_id: uuid.UUID, data: NoteIn, user: User = Depends(require_recruiter),
             db: Session = Depends(get_db)):
    return report_service.add_note(db, user, report_id, data.text)


@router.get("/{report_id}/pdf")
def pdf(report_id: uuid.UUID, user: User = Depends(require_recruiter), db: Session = Depends(get_db)):
    path = report_service.pdf_path(db, user, report_id)
    return FileResponse(path, media_type="application/pdf", filename=f"agenthire-report-{str(report_id)[:8]}.pdf",
                        headers={"Cache-Control": "private, no-store"})
