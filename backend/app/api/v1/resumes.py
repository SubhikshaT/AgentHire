import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_recruiter
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.rate_limit import UPLOAD_LIMIT, limiter
from app.database.session import get_db
from app.models import User
from app.models.enums import ParsingStatus
from app.schemas.candidate import ResumeOut, UploadResult
from app.services import resume_service
from app.services.audit_service import log_action
from app.services.permissions import get_visible_resume
from app.utils.files import resolve_stored

router = APIRouter(tags=["resumes"])
MAX_FILES = 50


async def _read_limited(f: UploadFile) -> bytes:
    limit = get_settings().max_upload_bytes
    data = await f.read(limit + 1)
    return data  # size checked (with a clear message) in detect_type


@router.post("/resumes/upload", response_model=UploadResult, status_code=201)
@limiter.limit(UPLOAD_LIMIT)
async def upload(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    job_id: uuid.UUID | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Candidates upload their own resume. Recruiters must pass job_id."""
    data = await _read_limited(file)
    result = resume_service.upload_resume(db, user, file.filename or "", data, job_id)
    if not result.ok:
        status = 413 if result.error_code == "file_too_large" else 409 if result.error_code == "duplicate" else 400
        raise AppError(result.error or "Upload failed.", code=result.error_code or "upload_failed", status_code=status)
    if result.error_code != "duplicate_linked":
        background.add_task(resume_service.process_resume_job, result.resume_id)
    return result


@router.post("/jobs/{job_id}/resumes/bulk-upload", response_model=list[UploadResult], status_code=207)
@limiter.limit(UPLOAD_LIMIT)
async def bulk_upload(
    request: Request,
    job_id: uuid.UUID,
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    user: User = Depends(require_recruiter),
    db: Session = Depends(get_db),
):
    """Upload many resumes for one job. Each file gets its own result; bad files do not stop the batch."""
    if len(files) > MAX_FILES:
        raise AppError(f"Upload at most {MAX_FILES} files at a time.", code="too_many_files")
    results = []
    for f in files:
        data = await _read_limited(f)
        r = resume_service.upload_resume(db, user, f.filename or "", data, job_id)
        if r.ok and r.error_code != "duplicate_linked":
            background.add_task(resume_service.process_resume_job, r.resume_id)
        results.append(r)
    return results


@router.get("/resumes/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: uuid.UUID, include_text: bool = False, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    r = get_visible_resume(db, user, resume_id)
    out = ResumeOut.model_validate(r)
    if not include_text:
        out.extracted_text = None
    return out


@router.get("/resumes/{resume_id}/status")
def status(resume_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = get_visible_resume(db, user, resume_id)
    meta = r.extraction_metadata or {}
    return {"id": r.id, "parsing_status": r.parsing_status, "parsing_error": r.parsing_error,
            "candidate_id": r.candidate_id, "skills_found": meta.get("skills_found"),
            "warnings": meta.get("warnings", [])}


@router.get("/resumes/{resume_id}/file")
def download(resume_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = get_visible_resume(db, user, resume_id)
    path = resolve_stored(r.stored_path)
    if not path.exists():
        raise AppError("The stored file is missing.", code="file_missing", status_code=404)
    media = "application/pdf" if r.file_type == "pdf" else \
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(path, media_type=media, filename=r.original_filename,
                        content_disposition_type="inline" if r.file_type == "pdf" else "attachment",
                        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@router.post("/resumes/{resume_id}/reprocess", response_model=ResumeOut)
def reprocess(resume_id: uuid.UUID, background: BackgroundTasks, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    r = get_visible_resume(db, user, resume_id)
    if r.parsing_status == ParsingStatus.PROCESSING:
        raise AppError("This resume is being processed right now.", code="busy", status_code=409)
    resume_service.reset_for_reprocess(db, r)
    log_action(db, user.id, "resume.reprocess", "resume", r.id)
    db.commit()
    background.add_task(resume_service.process_resume_job, r.id)
    return ResumeOut.model_validate(r)
