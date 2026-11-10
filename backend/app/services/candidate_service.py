"""Candidate profiles: listing, details, manual corrections, deletion."""
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.ai.taxonomy import get_taxonomy
from app.core.exceptions import AppError
from app.models import (
    Application,
    CandidateMatch,
    CandidateProfile,
    CandidateSkill,
    Job,
    Resume,
    Skill,
    User,
)
from app.models.enums import VerificationStatus
from app.schemas.candidate import CandidateSkillOut, CandidateUpdate, ResumeBrief, SkillsUpdate
from app.services.audit_service import log_action
from app.services.permissions import get_visible_candidate
from app.services.resume_service import get_or_create_skill
from app.utils.files import resolve_stored

EDU_RANK = {"phd": 6, "masters": 5, "bachelors": 4, "diploma": 3, "higher_secondary": 2, "secondary": 1}


def highest_education(profile: CandidateProfile) -> str | None:
    best = None
    for e in profile.education or []:
        lvl = e.get("level")
        if lvl and (best is None or EDU_RANK.get(lvl, 0) > EDU_RANK.get(best.get("level"), 0)):
            best = e
    if not best:
        return None
    return best.get("degree") or best.get("level")


def skills_out(profile: CandidateProfile) -> list[CandidateSkillOut]:
    order = {"skills": 0, "experience": 1, "projects": 2}
    items = sorted(profile.skills, key=lambda cs: (order.get(cs.evidence_section or "", 5), cs.skill.name.lower()))
    return [
        CandidateSkillOut(
            id=cs.id, skill_key=cs.skill.normalized_name, name=cs.skill.name, category=cs.skill.category,
            evidence_text=cs.evidence_text, evidence_section=cs.evidence_section,
            verification_status=cs.verification_status, proficiency_level=cs.proficiency_level,
        )
        for cs in items
    ]


def applications_summary(db: Session, profile_id: uuid.UUID, recruiter_id: uuid.UUID | None) -> list[dict]:
    stmt = (
        select(Application, Job, CandidateMatch)
        .join(Job, Job.id == Application.job_id)
        .outerjoin(CandidateMatch, CandidateMatch.application_id == Application.id)
        .where(Application.candidate_id == profile_id)
        .order_by(Application.created_at.desc())
    )
    if recruiter_id:
        stmt = stmt.where(Job.recruiter_id == recruiter_id)
    return [
        {
            "application_id": str(a.id), "job_id": str(j.id), "job_title": j.title, "stage": a.stage,
            "overall_score": m.overall_score if m else None, "match_id": str(m.id) if m else None,
            "created_at": a.created_at.isoformat(),
        }
        for a, j, m in db.execute(stmt).all()
    ]


def list_for_recruiter(db: Session, user: User, *, page: int, page_size: int, q: str | None, job_id: uuid.UUID | None,
                       stage: str | None, skill: str | None, min_experience: float | None, sort: str):
    visible = (
        select(Application.candidate_id)
        .join(Job, Job.id == Application.job_id)
        .where(Job.recruiter_id == user.id)
    )
    if job_id:
        visible = visible.where(Application.job_id == job_id)
    if stage:
        visible = visible.where(Application.stage == stage)
    stmt = select(CandidateProfile).where(CandidateProfile.id.in_(visible))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(CandidateProfile.full_name.ilike(like), CandidateProfile.email.ilike(like),
                              CandidateProfile.professional_summary.ilike(like)))
    if skill:
        key = get_taxonomy().resolve(skill) or skill.strip().lower()
        stmt = stmt.where(CandidateProfile.id.in_(
            select(CandidateSkill.candidate_id).join(Skill).where(Skill.normalized_name == key)))
    if min_experience is not None:
        stmt = stmt.where(CandidateProfile.total_experience_years >= min_experience)

    score_sq = None
    if job_id:
        score_sq = (
            select(Application.candidate_id, CandidateMatch.overall_score.label("score"))
            .join(CandidateMatch, CandidateMatch.application_id == Application.id)
            .where(Application.job_id == job_id)
            .subquery()
        )
        stmt = stmt.outerjoin(score_sq, score_sq.c.candidate_id == CandidateProfile.id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    orders = {
        "name": CandidateProfile.full_name.asc().nulls_last(),
        "-experience": CandidateProfile.total_experience_years.desc().nulls_last(),
        "experience": CandidateProfile.total_experience_years.asc().nulls_last(),
        "-created_at": CandidateProfile.created_at.desc(),
    }
    if sort == "-score" and score_sq is not None:
        order = score_sq.c.score.desc().nulls_last()
    else:
        order = orders.get(sort, CandidateProfile.created_at.desc())
    profiles = db.scalars(stmt.order_by(order, CandidateProfile.id).offset((page - 1) * page_size).limit(page_size)).all()
    items = []
    for p in profiles:
        sk = skills_out(p)
        items.append({
            "id": p.id, "full_name": p.full_name, "email": p.email,
            "total_experience_years": p.total_experience_years,
            "top_skills": [s.name for s in sk[:8]], "highest_education": highest_education(p),
            "is_synthetic": p.is_synthetic, "has_account": p.user_id is not None,
            "applications": applications_summary(db, p.id, user.id), "created_at": p.created_at,
        })
    return items, total


def detail(db: Session, user: User, profile: CandidateProfile) -> dict:
    resumes = db.scalars(select(Resume).where(Resume.candidate_id == profile.id).order_by(Resume.uploaded_at.desc())).all()
    return {
        "id": profile.id, "full_name": profile.full_name, "email": profile.email, "phone": profile.phone,
        "professional_summary": profile.professional_summary,
        "total_experience_years": profile.total_experience_years,
        "education": profile.education or [], "work_experience": profile.work_experience or [],
        "projects": profile.projects or [], "certifications": profile.certifications or [],
        "field_verification": profile.field_verification or {}, "is_synthetic": profile.is_synthetic,
        "has_account": profile.user_id is not None, "skills": skills_out(profile),
        "resumes": [ResumeBrief.model_validate(r) for r in resumes],
        "applications": applications_summary(db, profile.id, user.id if user.role == "recruiter" else None),
        "created_at": profile.created_at, "updated_at": profile.updated_at,
    }


def update_profile(db: Session, user: User, candidate_id: uuid.UUID, data: CandidateUpdate) -> CandidateProfile:
    profile = get_visible_candidate(db, user, candidate_id)
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise AppError("Nothing to update.", code="empty_update")
    if "email" in changes and profile.user_id is not None and changes["email"] != profile.email:
        raise AppError("The email of a registered candidate is their login email and cannot be changed here.",
                       code="email_locked")
    fv = dict(profile.field_verification or {})
    for field, value in changes.items():
        setattr(profile, field, value)
        fv[field] = VerificationStatus.MANUALLY_VERIFIED
    profile.field_verification = fv
    log_action(db, user.id, "candidate.corrected", "candidate_profile", profile.id, {"fields": sorted(changes)})
    db.commit()
    return profile


def replace_skills(db: Session, user: User, candidate_id: uuid.UUID, data: SkillsUpdate) -> CandidateProfile:
    profile = get_visible_candidate(db, user, candidate_id)
    tax = get_taxonomy()
    current = {cs.skill.normalized_name: cs for cs in profile.skills}
    wanted: dict[str, tuple] = {}
    for s in data.skills:
        key = tax.resolve(s.name) or s.name.strip().lower()
        wanted[key] = (s, key in tax.skills)
    for key, cs in current.items():
        if key not in wanted:
            db.delete(cs)
    for key, (s, _known) in wanted.items():
        cs = current.get(key)
        if cs is None:
            skill = get_or_create_skill(db, key) if key in tax.skills else _custom_skill(db, key, s.name)
            db.add(CandidateSkill(candidate_id=profile.id, skill_id=skill.id, evidence_text=s.evidence_text,
                                  evidence_section="manual", proficiency_level=s.proficiency_level,
                                  verification_status=VerificationStatus.MANUALLY_VERIFIED))
        else:
            changed = (s.evidence_text is not None and s.evidence_text != cs.evidence_text) or (
                s.proficiency_level != cs.proficiency_level)
            if s.evidence_text is not None:
                cs.evidence_text = s.evidence_text
            cs.proficiency_level = s.proficiency_level
            if changed:
                cs.verification_status = VerificationStatus.MANUALLY_VERIFIED
    fv = dict(profile.field_verification or {})
    fv["skills"] = VerificationStatus.MANUALLY_VERIFIED
    profile.field_verification = fv
    log_action(db, user.id, "candidate.skills_edited", "candidate_profile", profile.id, {"count": len(wanted)})
    db.commit()
    db.refresh(profile)
    return profile


def _custom_skill(db: Session, key: str, display: str) -> Skill:
    skill = db.scalar(select(Skill).where(Skill.normalized_name == key))
    if skill is None:
        skill = Skill(name=display.strip()[:120], normalized_name=key[:120], category="custom")
        db.add(skill)
        db.flush()
    return skill


def delete_candidate(db: Session, user: User, candidate_id: uuid.UUID) -> None:
    profile = get_visible_candidate(db, user, candidate_id)
    if user.role == "recruiter" and profile.user_id is not None:
        raise AppError(
            "This candidate has their own account. You can remove them from your jobs, but only they can delete "
            "their profile.", code="owned_by_candidate", status_code=403)
    paths = [r.stored_path for r in db.scalars(select(Resume).where(Resume.candidate_id == profile.id)).all()]
    log_action(db, user.id, "candidate.deleted", "candidate_profile", profile.id)
    db.delete(profile)
    db.commit()
    for p in paths:
        try:
            resolve_stored(p).unlink(missing_ok=True)
        except Exception:
            pass
