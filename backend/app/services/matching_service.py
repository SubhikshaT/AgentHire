"""Runs the Matching Agent for applications and stores explainable results."""
import time
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.agents.matching_agent import CandidateIn, CandidateSkillIn, JobIn, build_profile_text, score
from app.ai.embeddings.model import EmbeddingError, embed, embed_one, model_name
from app.ai.rag.retriever import top_chunks
from app.core.exceptions import AppError, NotFoundError
from app.models import Application, CandidateMatch, CandidateProfile, Job, Resume, User
from app.models.enums import ParsingStatus, VerificationStatus
from app.services.audit_service import log_action
from app.services.job_service import job_text_for_embedding
from app.services.permissions import get_own_job, get_visible_application
from app.services.settings_service import matching_weights

METHOD_VERSION = "hybrid-1.0"


def profile_text(p: CandidateProfile) -> str:
    return build_profile_text(p.professional_summary, [cs.skill.name for cs in p.skills], p.work_experience,
                              p.projects, p.education)


def latest_resume(db: Session, candidate_id) -> Resume | None:
    return db.scalar(select(Resume).where(Resume.candidate_id == candidate_id,
                                          Resume.parsing_status == ParsingStatus.COMPLETED)
                     .order_by(Resume.uploaded_at.desc()).limit(1))


def candidate_input(db: Session, p: CandidateProfile, resume: Resume | None, embedding=None) -> CandidateIn:
    return CandidateIn(
        skills=[CandidateSkillIn(key=cs.skill.normalized_name, name=cs.skill.name, evidence_text=cs.evidence_text,
                                 evidence_section=cs.evidence_section,
                                 verified=cs.verification_status == VerificationStatus.MANUALLY_VERIFIED)
                for cs in p.skills],
        total_experience_years=p.total_experience_years,
        education=p.education or [],
        certifications=p.certifications or [],
        profile_text=profile_text(p),
        raw_text=(resume.extracted_text if resume else "") or "",
        profile_embedding=embedding,
    )


def ensure_job_embedding(db: Session, job: Job) -> list[float]:
    if job.embedding is None or job.embedding_model != model_name():
        job.embedding = embed_one(job_text_for_embedding(job))
        job.embedding_model = model_name()
        db.flush()
    return list(job.embedding)


def job_input(job: Job, emb) -> JobIn:
    return JobIn(title=job.title, required_skills=job.required_skills or [], preferred_skills=job.preferred_skills or [],
                 minimum_experience=job.minimum_experience, education_requirements=job.education_requirements or [],
                 certifications=job.certifications or [], requirements_text=job_text_for_embedding(job), embedding=emb)


def _closest_evidence(db: Session, resume: Resume | None, skills: list[str]) -> list[dict]:
    """RAG step: for each missing / related skill, retrieve the closest resume chunk as context."""
    if resume is None or not skills:
        return []
    vecs = embed([f"Experience with {s}" for s in skills])
    out = []
    for s, v in zip(skills, vecs):
        hits = top_chunks(db, resume.id, v, k=1)
        if hits:
            out.append({"skill": s, **hits[0]})
    return out


def run_for_job(db: Session, user: User, job_id: uuid.UUID) -> dict:
    job = get_own_job(db, user, job_id)
    if not job.required_skills:
        raise AppError("Add required skills to the job before running matching.", code="missing_required_skills")
    t0 = time.perf_counter()
    weights = matching_weights(db, user.id)
    try:
        jemb = ensure_job_embedding(db, job)
    except EmbeddingError as e:
        raise AppError(f"Semantic model unavailable: {e}", code="embedding_unavailable", status_code=503) from None
    jin = job_input(job, jemb)
    apps = db.scalars(select(Application).where(Application.job_id == job.id)).all()
    pending = 0
    scored = 0
    profiles, resumes, targets = [], [], []
    for app in apps:
        r = latest_resume(db, app.candidate_id)
        if r is None:
            pending += 1
            continue
        targets.append(app)
        profiles.append(db.get(CandidateProfile, app.candidate_id))
        resumes.append(r)
    embs = embed([profile_text(p) for p in profiles]) if profiles else []
    for app, p, r, e in zip(targets, profiles, resumes, embs):
        cin = candidate_input(db, p, r, e.tolist())
        res = score(jin, cin, weights)
        need = res.explanation["required_skills"]["missing"] + [x["skill"] for x in res.explanation["required_skills"]["related"]]
        res.explanation["required_skills"]["closest_evidence"] = _closest_evidence(db, r, need[:6])
        res.explanation["method_version"] = METHOD_VERSION
        res.explanation["embedding_model"] = model_name()
        res.explanation["resume_id"] = str(r.id)
        m = db.scalar(select(CandidateMatch).where(CandidateMatch.application_id == app.id))
        if m is None:
            m = CandidateMatch(application_id=app.id)
            db.add(m)
        c = res.components
        m.semantic_score = c["semantic"]
        m.required_skill_score = c["required_skills"]
        m.preferred_skill_score = c["preferred_skills"]
        m.experience_score = c["experience"]
        m.education_score = c["education"]
        m.certification_score = c["certifications"]
        m.keyword_baseline_score = res.keyword_baseline
        m.overall_score = res.overall
        m.weights_used = weights
        m.explanation = res.explanation
        from app.database.base import utcnow
        m.calculated_at = utcnow()
        scored += 1
    log_action(db, user.id, "matching.run", "job", job.id, {"scored": scored, "pending": pending})
    db.commit()
    return {"job_id": job.id, "scored": scored, "skipped_no_parsed_resume": pending,
            "duration_ms": int((time.perf_counter() - t0) * 1000), "weights": weights}


def match_out(db: Session, m: CandidateMatch) -> dict:
    app = m.application
    c = app.candidate
    return {
        "id": m.id, "application_id": app.id, "candidate_id": c.id, "candidate_name": c.full_name,
        "is_synthetic": c.is_synthetic, "job_id": app.job_id, "job_title": app.job.title, "stage": app.stage,
        "overall_score": m.overall_score, "keyword_baseline_score": m.keyword_baseline_score,
        "components": {
            "semantic": m.semantic_score, "required_skills": m.required_skill_score,
            "preferred_skills": m.preferred_skill_score, "experience": m.experience_score,
            "education": m.education_score, "certifications": m.certification_score,
        },
        "weights_used": m.weights_used, "explanation": m.explanation, "calculated_at": m.calculated_at,
    }


def results_for_job(db: Session, user: User, job_id: uuid.UUID) -> list[dict]:
    get_own_job(db, user, job_id)
    rows = db.scalars(select(CandidateMatch).join(Application).where(Application.job_id == job_id)
                      .order_by(CandidateMatch.overall_score.desc())).all()
    out = []
    for rank, m in enumerate(rows, start=1):
        d = match_out(db, m)
        d["rank"] = rank
        out.append(d)
    return out


def get_match(db: Session, user: User, match_id: uuid.UUID) -> dict:
    m = db.get(CandidateMatch, match_id)
    if m is None:
        raise NotFoundError("Match not found.")
    get_visible_application(db, user, m.application_id)
    return match_out(db, m)


def compare(db: Session, user: User, job_id: uuid.UUID, candidate_ids: list[uuid.UUID]) -> dict:
    job = get_own_job(db, user, job_id)
    if not 2 <= len(set(candidate_ids)) <= 4:
        raise AppError("Choose 2 to 4 candidates to compare.", code="bad_selection", status_code=422)
    rows = []
    for cid in dict.fromkeys(candidate_ids):
        app = db.scalar(select(Application).where(Application.job_id == job.id, Application.candidate_id == cid))
        if app is None:
            raise NotFoundError("One of the candidates has not applied to this job.")
        m = db.scalar(select(CandidateMatch).where(CandidateMatch.application_id == app.id))
        rows.append(match_out(db, m) if m else {"candidate_id": cid, "candidate_name": app.candidate.full_name,
                                                 "overall_score": None, "explanation": None})
    skills = job.required_skills + job.preferred_skills
    matrix = []
    for s in skills:
        row = {"skill": s, "required": s in job.required_skills, "candidates": []}
        for r in rows:
            exp = r.get("explanation") or {}
            group = exp.get("required_skills" if s in job.required_skills else "preferred_skills", {})
            status_, evidence = "missing", None
            for x in group.get("matched", []):
                if x["skill"] == s:
                    status_, evidence = "matched", x.get("evidence_text")
            for x in group.get("related", []):
                if x["skill"] == s:
                    status_, evidence = "related", x.get("note")
            if not exp:
                status_ = "not_scored"
            row["candidates"].append({"candidate_id": str(r["candidate_id"]), "status": status_, "evidence": evidence})
        matrix.append(row)
    return {"job_id": job.id, "job_title": job.title, "candidates": rows, "skill_matrix": matrix}
