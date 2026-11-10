"""Resume upload, background processing and candidate-profile updates.

Pipeline: validate -> store -> extract text -> clean -> sections -> fields/skills
          -> profile update -> chunk -> embed -> store -> link duplicates by email
"""
import logging
import time
import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.agents.resume_agent import ResumeIntelligenceAgent
from app.ai.embeddings.model import EmbeddingError, embed, model_name
from app.ai.parsing.extract import ExtractionError, extract_text
from app.ai.parsing.sections import clean_text, split_sections
from app.ai.rag.chunker import chunk_sections
from app.ai.schemas.resume import ParsedResume
from app.ai.taxonomy import get_taxonomy
from app.core.exceptions import AppError, NotFoundError
from app.database.session import SessionLocal
from app.models import (
    Application,
    CandidateProfile,
    CandidateSkill,
    Job,
    Resume,
    ResumeChunk,
    Skill,
    StageHistory,
    User,
)
from app.models.enums import ApplicationSource, ParsingStatus, Role, Stage, VerificationStatus
from app.schemas.candidate import UploadResult
from app.services.audit_service import log_action
from app.services.permissions import candidate_profile_of, get_own_job
from app.utils.files import FileValidationError, detect_type, resolve_stored, safe_display_name, sha256, store_upload

logger = logging.getLogger("agenthire.resumes")

PROFILE_FIELDS = ["full_name", "email", "phone", "professional_summary", "total_experience_years",
                  "education", "work_experience", "projects", "certifications"]


# ---------------------------------------------------------------- upload
def _create_application(db: Session, candidate_id: uuid.UUID, job_id: uuid.UUID, source: ApplicationSource,
                        actor: uuid.UUID | None) -> Application:
    app = Application(candidate_id=candidate_id, job_id=job_id, stage=Stage.APPLIED, source=source)
    db.add(app)
    db.flush()
    db.add(StageHistory(application_id=app.id, from_stage=None, to_stage=Stage.APPLIED, changed_by=actor,
                        note="Created by resume upload" if source == ApplicationSource.RECRUITER_UPLOAD else "Applied"))
    return app


def upload_resume(db: Session, user: User, filename: str, data: bytes, job_id: uuid.UUID | None) -> UploadResult:
    """Validate and store one file. Returns a result (never raises for a bad file)."""
    display = safe_display_name(filename)
    try:
        kind = detect_type(filename, data)
    except FileValidationError as e:
        return UploadResult(filename=display, ok=False, error_code=e.code, error=e.message)

    job: Job | None = None
    if user.role == Role.RECRUITER:
        if job_id is None:
            raise AppError("Choose a job to upload resumes for.", code="job_required")
        job = get_own_job(db, user, job_id)

    digest = sha256(data)
    existing = db.scalar(select(Resume).where(Resume.file_hash == digest))
    if existing is not None:
        # Same file already uploaded. For a recruiter, link that candidate to this job instead of duplicating.
        if user.role == Role.RECRUITER and existing.candidate_id:
            app = db.scalar(select(Application).where(Application.candidate_id == existing.candidate_id,
                                                      Application.job_id == job.id))
            if app is None:
                app = _create_application(db, existing.candidate_id, job.id, ApplicationSource.RECRUITER_UPLOAD, user.id)
                log_action(db, user.id, "resume.duplicate_linked", "resume", existing.id, {"job_id": str(job.id)})
                db.commit()
                return UploadResult(filename=display, ok=True, resume_id=existing.id,
                                    candidate_id=existing.candidate_id, application_id=app.id,
                                    error_code="duplicate_linked",
                                    error="Same file was uploaded before; the existing candidate was added to this job.")
        return UploadResult(filename=display, ok=False, resume_id=existing.id, error_code="duplicate",
                            error="This exact file has already been uploaded.")

    stored = store_upload(data, kind)
    if user.role == Role.CANDIDATE:
        profile = candidate_profile_of(db, user)
        if profile is None:
            profile = CandidateProfile(user_id=user.id, full_name=user.name, email=user.email)
            db.add(profile)
            db.flush()
        application = None
    else:
        profile = CandidateProfile(created_by=user.id)
        db.add(profile)
        db.flush()
        application = _create_application(db, profile.id, job.id, ApplicationSource.RECRUITER_UPLOAD, user.id)

    resume = Resume(candidate_id=profile.id, original_filename=display, stored_path=stored, file_type=kind,
                    file_hash=digest, parsing_status=ParsingStatus.PENDING, uploaded_by=user.id,
                    target_job_id=job.id if job else None, extraction_metadata={"size_bytes": len(data)})
    db.add(resume)
    db.flush()
    log_action(db, user.id, "resume.uploaded", "resume", resume.id, {"job_id": str(job.id) if job else None})
    db.commit()
    return UploadResult(filename=display, ok=True, resume_id=resume.id, candidate_id=profile.id,
                        application_id=application.id if application else None)


# ---------------------------------------------------------------- processing
def process_resume_job(resume_id: uuid.UUID) -> None:
    """Background-task entry point: uses its own DB session."""
    db = SessionLocal()
    try:
        process_resume(db, resume_id)
    except Exception:
        logger.exception("Unexpected error while processing resume %s", resume_id)
        db.rollback()
        r = db.get(Resume, resume_id)
        if r is not None:
            r.parsing_status = ParsingStatus.FAILED
            r.parsing_error = "Unexpected server error while processing this resume."
            db.commit()
    finally:
        db.close()


def process_resume(db: Session, resume_id: uuid.UUID) -> Resume:
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise NotFoundError("Resume not found.")
    resume.parsing_status = ParsingStatus.PROCESSING
    resume.parsing_error = None
    db.commit()
    t0 = time.perf_counter()

    try:
        data = resolve_stored(resume.stored_path).read_bytes()
    except (OSError, AppError):
        return _fail(db, resume, "The stored file is missing. Please upload it again.")
    try:
        raw, file_meta = extract_text(data, resume.file_type)
    except ExtractionError as e:
        return _fail(db, resume, str(e))

    text = clean_text(raw)
    agent = ResumeIntelligenceAgent()
    parsed = agent.parse(text)
    resume.extracted_text = text

    profile = db.get(CandidateProfile, resume.candidate_id) if resume.candidate_id else None
    profile = _merge_duplicate_profile(db, resume, profile, parsed)
    owner_is_other = profile.user_id is not None and resume.uploaded_by != profile.user_id
    _update_profile(db, profile, parsed, only_fill_empty=owner_is_other)
    _replace_auto_skills(db, profile, parsed)

    # chunk + embed (with retry); parsing is still kept if embedding fails
    db.execute(delete(ResumeChunk).where(ResumeChunk.resume_id == resume.id))
    chunks = chunk_sections(split_sections(text))
    emb_error = None
    vectors = None
    for attempt in range(3):
        try:
            vectors = embed([c[2] for c in chunks]) if chunks else None
            break
        except EmbeddingError as e:
            emb_error = str(e)
            time.sleep(0.5 * (attempt + 1))
    for i, (section, idx, chunk_text) in enumerate(chunks):
        db.add(ResumeChunk(
            resume_id=resume.id, section=section, chunk_index=idx, chunk_text=chunk_text,
            embedding=vectors[i].tolist() if vectors is not None else None,
            embedding_model=model_name() if vectors is not None else None,
        ))

    resume.parsing_status = ParsingStatus.COMPLETED
    resume.extraction_metadata = {
        **(resume.extraction_metadata or {}),
        **file_meta,
        "agent_version": agent.version,
        "taxonomy_version": get_taxonomy().version,
        "sections_found": parsed.sections_found,
        "warnings": parsed.warnings + ([f"Embedding failed: {emb_error}"] if vectors is None and chunks else []),
        "skills_found": len(parsed.skills),
        "chunks": len(chunks),
        "embedding_model": model_name() if vectors is not None else None,
        "processing_ms": int((time.perf_counter() - t0) * 1000),
        "parsed": parsed.model_dump(mode="json"),
    }
    db.commit()
    return resume


def _fail(db: Session, resume: Resume, message: str) -> Resume:
    resume.parsing_status = ParsingStatus.FAILED
    resume.parsing_error = message
    db.commit()
    return resume


def _merge_duplicate_profile(db: Session, resume: Resume, profile: CandidateProfile | None,
                             parsed: ParsedResume) -> CandidateProfile:
    """If a recruiter-imported placeholder turns out to be someone who already has a profile
    (same email), move the resume and applications to that profile and drop the placeholder."""
    if profile is None:
        profile = CandidateProfile(created_by=resume.uploaded_by)
        db.add(profile)
        db.flush()
        resume.candidate_id = profile.id
    if not parsed.email or profile.user_id is not None:
        return profile
    other = db.scalar(
        select(CandidateProfile)
        .where(CandidateProfile.email == parsed.email, CandidateProfile.id != profile.id)
        .order_by(CandidateProfile.user_id.is_(None), CandidateProfile.created_at)
        .limit(1)
    )
    if other is None:
        return profile
    for app in db.scalars(select(Application).where(Application.candidate_id == profile.id)).all():
        clash = db.scalar(select(Application).where(Application.candidate_id == other.id, Application.job_id == app.job_id))
        if clash:
            db.delete(app)
        else:
            app.candidate_id = other.id
    for r in db.scalars(select(Resume).where(Resume.candidate_id == profile.id)).all():
        r.candidate_id = other.id
    db.flush()
    log_action(db, resume.uploaded_by, "candidate_profile.merged", "candidate_profile", other.id,
               {"merged_from": str(profile.id), "reason": "same email"})
    db.delete(profile)
    db.flush()
    return other


def _update_profile(db: Session, profile: CandidateProfile, p: ParsedResume, only_fill_empty: bool) -> None:
    verified = profile.field_verification or {}
    values = {
        "full_name": p.candidate_name,
        "email": p.email,
        "phone": p.phone,
        "professional_summary": p.professional_summary,
        "total_experience_years": p.total_experience_years,
        "education": [e.model_dump() for e in p.education],
        "work_experience": [e.model_dump() for e in p.work_experience],
        "projects": [e.model_dump() for e in p.projects],
        "certifications": [e.model_dump() for e in p.certifications],
    }
    for field, val in values.items():
        if verified.get(field) == VerificationStatus.MANUALLY_VERIFIED:
            continue
        cur = getattr(profile, field)
        if field == "email" and profile.user_id is not None and cur:
            continue  # never overwrite the account owner's email
        if only_fill_empty and cur not in (None, [], ""):
            continue
        if val in (None, []) and cur not in (None, [], "") and field in ("full_name", "email"):
            continue
        setattr(profile, field, val)
    fv = dict(verified)
    for field in PROFILE_FIELDS:
        fv.setdefault(field, VerificationStatus.AUTO_EXTRACTED)
    profile.field_verification = fv


def get_or_create_skill(db: Session, key: str) -> Skill:
    tax = get_taxonomy()
    skill = db.scalar(select(Skill).where(Skill.normalized_name == key))
    if skill is None:
        sd = tax.skills.get(key)
        skill = Skill(name=sd.display if sd else key, normalized_name=key, category=sd.category if sd else "custom")
        db.add(skill)
        db.flush()
    return skill


def _replace_auto_skills(db: Session, profile: CandidateProfile, p: ParsedResume) -> None:
    existing = db.scalars(select(CandidateSkill).where(CandidateSkill.candidate_id == profile.id)).all()
    manual_keys = set()
    for cs in existing:
        if cs.verification_status == VerificationStatus.MANUALLY_VERIFIED:
            manual_keys.add(cs.skill.normalized_name)
        else:
            db.delete(cs)
    db.flush()
    for s in p.skills:
        if s.key in manual_keys:
            continue
        skill = get_or_create_skill(db, s.key)
        db.add(CandidateSkill(candidate_id=profile.id, skill_id=skill.id, evidence_text=s.evidence_text,
                              evidence_section=s.evidence_section,
                              verification_status=VerificationStatus.AUTO_EXTRACTED))
    db.flush()


def reset_for_reprocess(db: Session, resume: Resume) -> None:
    resume.parsing_status = ParsingStatus.PENDING
    resume.parsing_error = None
    db.commit()
