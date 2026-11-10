"""Interviews: create, generate questions, edit, run (serve / draft / submit), complete, evaluate."""
import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.agents.evaluation_agent import (
    PROMPT_VERSION as EVAL_PROMPT,
    concept_coverage,
    evaluate_with_llm,
    evaluate_with_rules,
    insufficient_result,
    is_insufficient,
    weighted,
)
from app.ai.agents.interview_agent import (
    CATEGORIES,
    PROMPT_VERSION as QGEN_PROMPT,
    GeneratedQuestion,
    InterviewContext,
    InterviewGenerationAgent,
    default_time_limit,
    rubric_from_concepts,
)
from app.ai.embeddings.model import EmbeddingError, embed_one
from app.ai.providers import get_provider, llm_available
from app.ai.providers.base import LLMError
from app.ai.rag.retriever import top_chunks
from app.ai.rubric import RUBRIC_VERSION
from app.core.config import get_settings
from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.database.base import utcnow
from app.database.session import SessionLocal
from app.models import (
    Application,
    CandidateMatch,
    CandidateProfile,
    Interview,
    InterviewAnswer,
    InterviewQuestion,
    Job,
    StageHistory,
    User,
)
from app.models.enums import EvaluationStatus, InterviewStatus, InterviewType, QuestionSource, Role, Stage
from app.services import ai_audit_service
from app.services.audit_service import log_action
from app.services.matching_service import latest_resume
from app.services.permissions import candidate_profile_of, get_visible_application
from app.services.settings_service import rubric_weights

logger = logging.getLogger("agenthire.interviews")
STAGE_ORDER = [s.value for s in Stage]


# ----------------------------------------------------------------- access
def get_interview(db: Session, user: User, interview_id: uuid.UUID) -> Interview:
    iv = db.get(Interview, interview_id)
    if iv is None:
        raise NotFoundError("Interview not found.")
    get_visible_application(db, user, iv.application_id)  # raises 404 if not allowed
    return iv


def _is_candidate_owner(db: Session, user: User, iv: Interview) -> bool:
    if user.role != Role.CANDIDATE:
        return False
    p = candidate_profile_of(db, user)
    return p is not None and iv.application.candidate_id == p.id


def _can_manage(db: Session, user: User, iv: Interview) -> bool:
    """Recruiter of the job for assigned interviews; the candidate for their own practice interviews."""
    if user.role == Role.RECRUITER:
        return iv.application.job.recruiter_id == user.id
    return iv.interview_type == InterviewType.PRACTICE and _is_candidate_owner(db, user, iv)


def _advance_stage(db: Session, app: Application, to: Stage, actor: uuid.UUID | None, note: str) -> None:
    """Move forward only (never backwards, never to selected/rejected)."""
    if app.stage in (Stage.SELECTED, Stage.REJECTED):
        return
    if STAGE_ORDER.index(to.value) > STAGE_ORDER.index(app.stage):
        db.add(StageHistory(application_id=app.id, from_stage=app.stage, to_stage=to, changed_by=actor, note=note))
        app.stage = to


# ----------------------------------------------------------------- create / generate / edit
def create(db: Session, user: User, application_id: uuid.UUID, interview_type: str, question_count: int,
           difficulty: str, categories: list[str]) -> Interview:
    app = get_visible_application(db, user, application_id)
    if user.role == Role.CANDIDATE and interview_type != InterviewType.PRACTICE:
        raise ForbiddenError("Candidates can only create practice interviews.")
    if user.role == Role.RECRUITER and interview_type != InterviewType.ASSIGNED:
        raise ForbiddenError("Recruiters create assigned interviews.")
    bad = [c for c in categories if c not in CATEGORIES]
    if bad or not categories:
        raise AppError(f"Unknown categories: {bad}" if bad else "Choose at least one category.", code="bad_categories",
                       status_code=422)
    iv = Interview(application_id=app.id, created_by=user.id, interview_type=interview_type,
                   status=InterviewStatus.DRAFT, question_count=question_count, difficulty=difficulty,
                   categories=list(dict.fromkeys(categories)))
    db.add(iv)
    db.flush()
    log_action(db, user.id, "interview.created", "interview", iv.id, {"type": interview_type})
    db.commit()
    return iv


def _context(db: Session, iv: Interview) -> InterviewContext:
    app = iv.application
    job: Job = app.job
    p: CandidateProfile = app.candidate
    match = db.scalar(select(CandidateMatch).where(CandidateMatch.application_id == app.id))
    gaps: list[str] = []
    if match:
        ex = match.explanation or {}
        gaps = ex.get("required_skills", {}).get("missing", []) + [
            r["skill"] for r in ex.get("required_skills", {}).get("related", [])]
        gaps += ex.get("preferred_skills", {}).get("missing", [])
    else:
        have = {cs.skill.normalized_name for cs in p.skills}
        from app.ai.taxonomy import get_taxonomy
        tax = get_taxonomy()
        gaps = [s for s in job.required_skills if (tax.resolve(s) or s.lower()) not in have]
    chunks: list[str] = []
    resume = latest_resume(db, p.id)
    if resume is not None:
        try:
            q = embed_one(f"{job.title} project using {', '.join(job.required_skills[:5])}")
            chunks = [h["text"] for h in top_chunks(db, resume.id, q, k=3, sections=["projects", "experience"])]
        except EmbeddingError:
            chunks = []
    return InterviewContext(
        job_title=job.title, required_skills=job.required_skills or [], preferred_skills=job.preferred_skills or [],
        candidate_skills=[cs.skill.name for cs in p.skills], skill_gaps=gaps[:10],
        experience_years=p.total_experience_years,
        projects=[{"name": x.get("name", ""), "description": x.get("description", ""), "skills": x.get("skills", [])}
                  for x in (p.projects or []) if x.get("name")],
        project_chunks=chunks,
    )


def generate_questions(db: Session, user: User, interview_id: uuid.UUID, use_llm: bool | None = None) -> dict:
    iv = get_interview(db, user, interview_id)
    if not _can_manage(db, user, iv):
        raise ForbiddenError("You cannot change this interview.")
    if iv.status not in (InterviewStatus.DRAFT, InterviewStatus.READY):
        raise AppError("Questions can only be generated before the interview starts.", code="interview_started")
    ctx = _context(db, iv)
    agent = InterviewGenerationAgent()
    provider = get_provider()
    want_llm = llm_available() if use_llm is None else (use_llm and llm_available())
    notice = None
    questions: list[GeneratedQuestion] = []
    if want_llm:
        try:
            questions, meta = agent.with_llm(provider, ctx, iv.categories, iv.difficulty, iv.question_count,
                                             get_settings().llm_timeout_seconds)
            ai_audit_service.record(db, agent=agent.name, provider=meta.provider, model_id=meta.model_id,
                                    prompt_version=QGEN_PROMPT, input_refs={"interview_id": iv.id,
                                                                            "application_id": iv.application_id},
                                    output_ref_type="interview", output_ref_id=iv.id, duration_ms=meta.duration_ms,
                                    validation_passed=True, retry_count=meta.retries)
        except LLMError as e:
            ai_audit_service.record(db, agent=agent.name, provider=provider.name, model_id=provider.model_id,
                                    prompt_version=QGEN_PROMPT, input_refs={"interview_id": iv.id},
                                    validation_passed=False, retry_count=getattr(e, "attempts", 0),
                                    error_message=str(e))
            notice = f"The AI model could not generate questions ({e}). Questions were taken from the question bank."
            questions = []
    if len(questions) < iv.question_count:
        extra = agent.from_bank(ctx, iv.categories, iv.difficulty, iv.question_count - len(questions),
                                seed=int(iv.id.int % 100000))
        have = {q.question.lower() for q in questions}
        questions += [q for q in extra if q.question.lower() not in have]
        if not want_llm:
            notice = "No AI model is available, so questions come from the curated question bank."
    if not questions:
        raise AppError("No questions could be generated for these categories.", code="no_questions")
    for old in list(iv.questions):
        db.delete(old)
    db.flush()
    for i, q in enumerate(questions[: iv.question_count], start=1):
        db.add(InterviewQuestion(interview_id=iv.id, question_text=q.question, category=q.category,
                                 difficulty=q.difficulty, expected_concepts=q.expected_concepts,
                                 evaluation_rubric=q.evaluation_rubric, time_limit_seconds=q.time_limit_seconds,
                                 source=q.source, grounding=q.grounding, sequence_number=float(i)))
    iv.status = InterviewStatus.READY
    if iv.interview_type == InterviewType.ASSIGNED:
        _advance_stage(db, iv.application, Stage.INTERVIEW_SCHEDULED, user.id, "Interview questions prepared")
    log_action(db, user.id, "interview.questions_generated", "interview", iv.id,
               {"count": len(questions), "llm": want_llm and not notice})
    db.commit()
    db.refresh(iv)
    return {"interview": interview_out(db, user, iv), "notice": notice}


def replace_questions(db: Session, user: User, interview_id: uuid.UUID, items: list[dict]) -> Interview:
    iv = get_interview(db, user, interview_id)
    if not _can_manage(db, user, iv):
        raise ForbiddenError("You cannot change this interview.")
    if iv.status not in (InterviewStatus.DRAFT, InterviewStatus.READY):
        raise AppError("Questions cannot be edited after the interview has started.", code="interview_started")
    old = {str(q.id): q for q in iv.questions}
    keep_ids = set()
    for i, it in enumerate(items, start=1):
        qid = it.get("id")
        concepts = [c for c in it.get("expected_concepts", []) if c.strip()] or ["clear, correct explanation"]
        if qid and qid in old:
            q = old[qid]
            changed = (q.question_text != it["question"] or q.expected_concepts != concepts)
            q.question_text = it["question"]
            q.category = it["category"]
            q.difficulty = it["difficulty"]
            q.expected_concepts = concepts
            q.evaluation_rubric = it.get("evaluation_rubric") or rubric_from_concepts(concepts)
            q.time_limit_seconds = it.get("time_limit_seconds") or default_time_limit(it["category"], it["difficulty"])
            q.sequence_number = float(i)
            if changed and q.source != QuestionSource.RECRUITER:
                q.grounding = ((q.grounding or "") + " · edited by a person").strip(" ·")[:400]
            keep_ids.add(qid)
        else:
            db.add(InterviewQuestion(
                interview_id=iv.id, question_text=it["question"], category=it["category"],
                difficulty=it["difficulty"], expected_concepts=concepts,
                evaluation_rubric=it.get("evaluation_rubric") or rubric_from_concepts(concepts),
                time_limit_seconds=it.get("time_limit_seconds") or default_time_limit(it["category"], it["difficulty"]),
                source=QuestionSource.RECRUITER, grounding="Written by a person", sequence_number=float(i)))
    for qid, q in old.items():
        if qid not in keep_ids:
            db.delete(q)
    iv.question_count = len(items)
    iv.status = InterviewStatus.READY if items else InterviewStatus.DRAFT
    from app.models import AIAuditLog
    for row in db.scalars(select(AIAuditLog).where(AIAuditLog.output_ref_id == iv.id,
                                                   AIAuditLog.agent == "interview_generation")).all():
        row.human_edited = True
    log_action(db, user.id, "interview.questions_edited", "interview", iv.id, {"count": len(items)})
    db.commit()
    db.refresh(iv)
    return iv


# ----------------------------------------------------------------- run
def start(db: Session, user: User, interview_id: uuid.UUID) -> Interview:
    iv = get_interview(db, user, interview_id)
    if not _is_candidate_owner(db, user, iv):
        raise ForbiddenError("Only the candidate can take this interview.")
    if iv.status == InterviewStatus.IN_PROGRESS:
        return iv  # resume
    if iv.status != InterviewStatus.READY:
        raise AppError("This interview is not ready to start.", code="not_ready")
    iv.status = InterviewStatus.IN_PROGRESS
    iv.started_at = utcnow()
    log_action(db, user.id, "interview.started", "interview", iv.id)
    db.commit()
    return iv


def _ordered(iv: Interview) -> list[InterviewQuestion]:
    return sorted(iv.questions, key=lambda q: q.sequence_number)


def current(db: Session, user: User, interview_id: uuid.UUID) -> dict:
    iv = get_interview(db, user, interview_id)
    if not _is_candidate_owner(db, user, iv):
        raise ForbiddenError("Only the candidate can take this interview.")
    if iv.status != InterviewStatus.IN_PROGRESS:
        raise AppError("The interview is not in progress.", code="not_in_progress")
    qs = _ordered(iv)
    answered = sum(1 for q in qs if q.answer and q.answer.is_final)
    nxt = next((q for q in qs if not (q.answer and q.answer.is_final)), None)
    if nxt is None:
        return {"done": True, "answered": answered, "total": len(qs)}
    ans = nxt.answer
    if ans is None:
        ans = InterviewAnswer(question_id=nxt.id, served_at=utcnow(), evaluation_status=EvaluationStatus.NOT_SUBMITTED)
        db.add(ans)
        db.commit()
    elapsed = (utcnow() - ans.served_at).total_seconds() if ans.served_at else 0
    return {
        "done": False, "answered": answered, "total": len(qs),
        "question": {"id": nxt.id, "number": answered + 1, "text": nxt.question_text, "category": nxt.category,
                     "category_label": CATEGORIES.get(nxt.category, nxt.category), "difficulty": nxt.difficulty,
                     "time_limit_seconds": nxt.time_limit_seconds, "is_follow_up": nxt.parent_question_id is not None},
        "draft_text": ans.draft_text or "",
        "seconds_remaining": max(0, int(nxt.time_limit_seconds - elapsed)),
        "served_at": ans.served_at,
    }


def _question_for(db: Session, user: User, interview_id: uuid.UUID, question_id: uuid.UUID):
    iv = get_interview(db, user, interview_id)
    if not _is_candidate_owner(db, user, iv):
        raise ForbiddenError("Only the candidate can answer this interview.")
    if iv.status != InterviewStatus.IN_PROGRESS:
        raise AppError("The interview is not in progress.", code="not_in_progress")
    q = db.get(InterviewQuestion, question_id)
    if q is None or q.interview_id != iv.id:
        raise NotFoundError("Question not found.")
    return iv, q


def save_draft(db: Session, user: User, interview_id: uuid.UUID, question_id: uuid.UUID, text: str) -> dict:
    _, q = _question_for(db, user, interview_id, question_id)
    ans = q.answer or InterviewAnswer(question_id=q.id, served_at=utcnow(),
                                      evaluation_status=EvaluationStatus.NOT_SUBMITTED)
    if ans.is_final:
        raise AppError("This answer was already submitted.", code="already_submitted", status_code=409)
    ans.draft_text = text
    ans.draft_saved_at = utcnow()
    db.add(ans)
    db.commit()
    return {"saved_at": ans.draft_saved_at}


def submit_answer(db: Session, user: User, interview_id: uuid.UUID, question_id: uuid.UUID, text: str) -> dict:
    iv, q = _question_for(db, user, interview_id, question_id)
    ans = q.answer or InterviewAnswer(question_id=q.id, served_at=utcnow())
    if ans.is_final:
        raise AppError("This answer was already submitted.", code="already_submitted", status_code=409)
    text = (text or "").strip()
    ans.answer_text = text
    ans.draft_text = None
    ans.is_final = True
    ans.submitted_at = utcnow()
    ans.concept_coverage = concept_coverage(text, q.expected_concepts or [])
    ans.evaluation_status = EvaluationStatus.PENDING_LLM
    db.add(ans)
    follow = None
    # at most one follow-up per question, only with an LLM and when key concepts are missing
    cov = ans.concept_coverage
    needs = (q.parent_question_id is None and not is_insufficient(text) and cov["missing"]
             and len(cov["missing"]) >= max(1, len(q.expected_concepts or []) // 2))
    already = db.scalar(select(func.count(InterviewQuestion.id)).where(InterviewQuestion.parent_question_id == q.id))
    if needs and not already and llm_available():
        provider = get_provider()
        try:
            fu, meta = InterviewGenerationAgent().follow_up(provider, q.question_text, q.expected_concepts,
                                                            text, cov["missing"], get_settings().llm_timeout_seconds)
            nq = InterviewQuestion(interview_id=iv.id, question_text=fu.question, category=q.category,
                                   difficulty=q.difficulty, expected_concepts=fu.expected_concepts,
                                   evaluation_rubric=rubric_from_concepts(fu.expected_concepts),
                                   time_limit_seconds=q.time_limit_seconds, source=QuestionSource.LLM,
                                   grounding="Follow-up to a previous answer", sequence_number=q.sequence_number + 0.5,
                                   parent_question_id=q.id)
            db.add(nq)
            db.flush()
            ai_audit_service.record(db, agent="interview_follow_up", provider=meta.provider, model_id=meta.model_id,
                                    prompt_version=QGEN_PROMPT, input_refs={"question_id": q.id},
                                    output_ref_type="interview_question", output_ref_id=nq.id,
                                    duration_ms=meta.duration_ms, validation_passed=True, retry_count=meta.retries)
            follow = str(nq.id)
        except LLMError as e:
            ai_audit_service.record(db, agent="interview_follow_up", provider=provider.name,
                                    model_id=provider.model_id, prompt_version=QGEN_PROMPT,
                                    input_refs={"question_id": q.id}, validation_passed=False, error_message=str(e))
    db.commit()
    return {"submitted": True, "follow_up_question_id": follow}


def complete(db: Session, user: User, interview_id: uuid.UUID) -> Interview:
    iv = get_interview(db, user, interview_id)
    if not _is_candidate_owner(db, user, iv):
        raise ForbiddenError("Only the candidate can finish this interview.")
    if iv.status != InterviewStatus.IN_PROGRESS:
        raise AppError("The interview is not in progress.", code="not_in_progress")
    for q in iv.questions:
        if not (q.answer and q.answer.is_final):
            ans = q.answer or InterviewAnswer(question_id=q.id)
            ans.answer_text = (ans.draft_text or "").strip() or None
            ans.is_final = True
            ans.submitted_at = utcnow()
            ans.concept_coverage = concept_coverage(ans.answer_text or "", q.expected_concepts or [])
            ans.evaluation_status = EvaluationStatus.PENDING_LLM
            ans.feedback = {**(ans.feedback or {}), "submitted_on_finish": True}
            db.add(ans)
    iv.status = InterviewStatus.COMPLETED
    iv.completed_at = utcnow()
    if iv.interview_type == InterviewType.ASSIGNED:
        _advance_stage(db, iv.application, Stage.INTERVIEW_COMPLETED, None, "Interview completed by candidate")
    log_action(db, user.id, "interview.completed", "interview", iv.id)
    db.commit()
    return iv


# ----------------------------------------------------------------- evaluation
def evaluate_job(interview_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        evaluate_pending(db, interview_id)
    except Exception:
        logger.exception("Evaluation failed for interview %s", interview_id)
    finally:
        db.close()


def evaluate_pending(db: Session, interview_id: uuid.UUID) -> dict:
    iv = db.get(Interview, interview_id)
    if iv is None:
        raise NotFoundError("Interview not found.")
    weights = rubric_weights(db, iv.application.job.recruiter_id)
    provider = get_provider()
    have_llm = llm_available()
    done = pending = failed = 0
    for q in _ordered(iv):
        ans = q.answer
        if ans is None or not ans.is_final or ans.evaluation_status == EvaluationStatus.EVALUATED:
            continue
        if is_insufficient(ans.answer_text):
            ev = insufficient_result(ans.answer_text, q.expected_concepts or [])
            _store_eval(ans, ev, weights, method="rule:insufficient_answer", dropped=0)
            ai_audit_service.record(db, agent="interview_evaluation", provider="rule", model_id=None,
                                    prompt_version=None, rubric_version=RUBRIC_VERSION,
                                    input_refs={"answer_id": ans.id, "question_id": q.id},
                                    output_ref_type="interview_answer", output_ref_id=ans.id,
                                    validation_passed=True)
            done += 1
            continue
        if not have_llm:
            ev = evaluate_with_rules(
                q.question_text,
                ans.answer_text,
                q.expected_concepts or []
            )
            _store_eval(ans, ev, weights, method="rule:concept_coverage", dropped=0)

            ai_audit_service.record(
            db,
            agent="interview_evaluation",
            provider="rule",
            model_id=None,
            prompt_version=None,
            rubric_version=RUBRIC_VERSION,
            input_refs={"answer_id": ans.id, "question_id": q.id},
            output_ref_type="interview_answer",
            output_ref_id=ans.id,
            validation_passed=True,
        )

        done += 1
        continue
        try:
            ev, meta, dropped = evaluate_with_llm(provider, q.question_text, q.expected_concepts or [],
                                                  q.evaluation_rubric or [], ans.answer_text, q.difficulty,
                                                  get_settings().llm_timeout_seconds)
            _store_eval(ans, ev, weights, method=f"llm:{meta.provider}", dropped=dropped)
            ai_audit_service.record(db, agent="interview_evaluation", provider=meta.provider, model_id=meta.model_id,
                                    prompt_version=EVAL_PROMPT, rubric_version=RUBRIC_VERSION,
                                    input_refs={"answer_id": ans.id, "question_id": q.id},
                                    output_ref_type="interview_answer", output_ref_id=ans.id,
                                    duration_ms=meta.duration_ms, validation_passed=True, retry_count=meta.retries)
            done += 1
        except LLMError as e:
            ans.evaluation_status = EvaluationStatus.FAILED
            ans.feedback = {**(ans.feedback or {}), "error": str(e)[:300]}
            ai_audit_service.record(db, agent="interview_evaluation", provider=provider.name,
                                    model_id=provider.model_id, prompt_version=EVAL_PROMPT,
                                    rubric_version=RUBRIC_VERSION, input_refs={"answer_id": ans.id},
                                    validation_passed=False, retry_count=getattr(e, "attempts", 0),
                                    error_message=str(e))
            failed += 1
    _update_total(iv)
    db.commit()
    return {"evaluated": done, "pending_llm": pending, "failed": failed, "total_score": iv.total_score,
            "llm_available": have_llm}


def _store_eval(ans: InterviewAnswer, ev, weights: dict, method: str, dropped: int) -> None:
    s = ev.scores
    ans.technical_score = s.technical_correctness
    ans.conceptual_score = s.conceptual_understanding
    ans.problem_solving_score = s.problem_solving
    ans.clarity_score = s.clarity
    ans.relevance_score = s.relevance
    ans.weighted_score = weighted(ev, weights)
    ans.verdict = ev.verdict
    ans.feedback = {
        "strengths": ev.strengths, "weaknesses": ev.weaknesses, "missing_concepts": ev.missing_concepts,
        "explanation": ev.explanation, "suggested_improvement": ev.suggested_improvement,
        "evidence_quotes": ev.evidence_quotes, "method": method, "rubric_version": RUBRIC_VERSION,
        "weights_used": weights, "quotes_dropped_not_in_answer": dropped,
        "submitted_on_finish": (ans.feedback or {}).get("submitted_on_finish", False),
    }
    ans.evaluation_status = EvaluationStatus.EVALUATED
    ans.evaluated_at = utcnow()


def _update_total(iv: Interview) -> None:
    answers = [q.answer for q in iv.questions if q.answer and q.answer.is_final]
    if answers and all(a.evaluation_status == EvaluationStatus.EVALUATED for a in answers):
        iv.total_score = round(sum(a.weighted_score or 0 for a in answers) / len(answers), 1)
    else:
        iv.total_score = None


def request_evaluation(db: Session, user: User, interview_id: uuid.UUID) -> dict:
    iv = get_interview(db, user, interview_id)
    if not _can_manage(db, user, iv):
        raise ForbiddenError("You cannot evaluate this interview.")
    if iv.status != InterviewStatus.COMPLETED:
        raise AppError("The interview is not finished yet.", code="not_completed")
    res = evaluate_pending(db, iv.id)
    log_action(db, user.id, "interview.evaluated", "interview", iv.id, res)
    db.commit()
    return res


# ----------------------------------------------------------------- read
def interview_out(db: Session, user: User, iv: Interview) -> dict:
    app = iv.application
    is_cand = user.role == Role.CANDIDATE
    hide_questions = is_cand and iv.status in (InterviewStatus.DRAFT, InterviewStatus.READY) \
        and iv.interview_type == InterviewType.ASSIGNED
    qs = []
    for q in _ordered(iv):
        a = q.answer
        item = {"id": q.id, "sequence_number": q.sequence_number, "question": q.question_text,
                "category": q.category, "category_label": CATEGORIES.get(q.category, q.category),
                "difficulty": q.difficulty, "time_limit_seconds": q.time_limit_seconds, "source": q.source,
                "grounding": q.grounding, "is_follow_up": q.parent_question_id is not None}
        if not is_cand or iv.status == InterviewStatus.COMPLETED:
            item["expected_concepts"] = q.expected_concepts
            item["evaluation_rubric"] = q.evaluation_rubric
        if a and a.is_final and (not is_cand or iv.status == InterviewStatus.COMPLETED):
            item["answer"] = {
                "text": a.answer_text, "submitted_at": a.submitted_at, "evaluation_status": a.evaluation_status,
                "verdict": a.verdict, "weighted_score": a.weighted_score,
                "scores": None if a.technical_score is None else {
                    "technical_correctness": a.technical_score, "conceptual_understanding": a.conceptual_score,
                    "problem_solving": a.problem_solving_score, "clarity": a.clarity_score,
                    "relevance": a.relevance_score},
                "feedback": a.feedback, "concept_coverage": a.concept_coverage, "evaluated_at": a.evaluated_at,
            }
        qs.append(item)
    return {
        "id": iv.id, "application_id": app.id, "job_id": app.job_id, "job_title": app.job.title,
        "candidate_id": app.candidate_id, "candidate_name": app.candidate.full_name,
        "interview_type": iv.interview_type, "status": iv.status, "difficulty": iv.difficulty,
        "categories": iv.categories, "question_count": iv.question_count, "started_at": iv.started_at,
        "completed_at": iv.completed_at, "total_score": iv.total_score, "created_at": iv.created_at,
        "questions": [] if hide_questions else qs,
        "questions_hidden_until_start": hide_questions,
        "can_manage": _can_manage(db, user, iv), "is_candidate": _is_candidate_owner(db, user, iv),
        "rubric_version": RUBRIC_VERSION,
    }


def list_for_user(db: Session, user: User, status: str | None = None) -> list[dict]:
    stmt = select(Interview).join(Application).join(Job)
    if user.role == Role.RECRUITER:
        stmt = stmt.where(Job.recruiter_id == user.id)
    else:
        p = candidate_profile_of(db, user)
        if p is None:
            return []
        stmt = stmt.where(Application.candidate_id == p.id)
    if status:
        stmt = stmt.where(Interview.status == status)
    out = []
    for iv in db.scalars(stmt.order_by(Interview.created_at.desc())).all():
        answers = [q.answer for q in iv.questions if q.answer and q.answer.is_final]
        out.append({"id": iv.id, "application_id": iv.application_id, "job_title": iv.application.job.title,
                    "candidate_name": iv.application.candidate.full_name, "interview_type": iv.interview_type,
                    "status": iv.status, "difficulty": iv.difficulty, "question_count": len(iv.questions),
                    "answered": len(answers), "total_score": iv.total_score,
                    "pending_evaluation": sum(1 for a in answers if a.evaluation_status != EvaluationStatus.EVALUATED),
                    "created_at": iv.created_at, "completed_at": iv.completed_at})
    return out
