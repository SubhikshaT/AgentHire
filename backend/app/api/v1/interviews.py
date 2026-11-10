import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rate_limit import LLM_LIMIT, limiter
from app.database.session import get_db
from app.models import User
from app.models.enums import InterviewStatus
from app.services import interview_service as svc

router = APIRouter(prefix="/interviews", tags=["interviews"])

Category = Literal["programming", "dsa", "dbms", "os", "networks", "software_engineering", "system_design",
                   "project", "behavioral"]
Difficulty = Literal["beginner", "intermediate", "advanced"]


class InterviewCreate(BaseModel):
    application_id: uuid.UUID
    interview_type: Literal["assigned", "practice"]
    question_count: int = Field(5, ge=3, le=15)
    difficulty: Difficulty = "intermediate"
    categories: list[Category] = Field(min_length=1, max_length=9)


class GenerateRequest(BaseModel):
    use_llm: bool | None = None


class QuestionIn(BaseModel):
    id: str | None = None
    question: str = Field(min_length=10, max_length=600)
    category: Category
    difficulty: Difficulty
    expected_concepts: list[str] = Field(default_factory=list, max_length=8)
    evaluation_rubric: list[str] | None = Field(default=None, max_length=8)
    time_limit_seconds: int | None = Field(default=None, ge=30, le=900)


class QuestionsUpdate(BaseModel):
    questions: list[QuestionIn] = Field(min_length=1, max_length=15)


class AnswerIn(BaseModel):
    text: str = Field(default="", max_length=8000)


@router.post("", status_code=201)
def create(data: InterviewCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    iv = svc.create(db, user, data.application_id, data.interview_type, data.question_count, data.difficulty,
                    list(data.categories))
    return svc.interview_out(db, user, iv)


@router.get("")
def list_interviews(status: InterviewStatus | None = None, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    return svc.list_for_user(db, user, status.value if status else None)


@router.get("/{interview_id}")
def get(interview_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.interview_out(db, user, svc.get_interview(db, user, interview_id))


@router.post("/{interview_id}/generate-questions")
@limiter.limit(LLM_LIMIT)
def generate(request: Request, interview_id: uuid.UUID, data: GenerateRequest | None = None,
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.generate_questions(db, user, interview_id, data.use_llm if data else None)


@router.put("/{interview_id}/questions")
def edit_questions(interview_id: uuid.UUID, data: QuestionsUpdate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    iv = svc.replace_questions(db, user, interview_id, [q.model_dump() for q in data.questions])
    return svc.interview_out(db, user, iv)


@router.post("/{interview_id}/start")
def start(interview_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    svc.start(db, user, interview_id)
    return svc.current(db, user, interview_id)


@router.get("/{interview_id}/current")
def current(interview_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.current(db, user, interview_id)


@router.put("/{interview_id}/answers/{question_id}/draft")
def draft(interview_id: uuid.UUID, question_id: uuid.UUID, data: AnswerIn, user: User = Depends(get_current_user),
          db: Session = Depends(get_db)):
    return svc.save_draft(db, user, interview_id, question_id, data.text)


@router.post("/{interview_id}/answers/{question_id}")
@limiter.limit(LLM_LIMIT)
def submit(request: Request, interview_id: uuid.UUID, question_id: uuid.UUID, data: AnswerIn,
           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.submit_answer(db, user, interview_id, question_id, data.text)


@router.post("/{interview_id}/complete")
def complete(interview_id: uuid.UUID, background: BackgroundTasks, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    iv = svc.complete(db, user, interview_id)
    background.add_task(svc.evaluate_job, iv.id)
    return svc.interview_out(db, user, iv)


@router.post("/{interview_id}/evaluate")
@limiter.limit(LLM_LIMIT)
def evaluate(request: Request, interview_id: uuid.UUID, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    """Evaluate answers that are still pending (needs an LLM for real answers)."""
    return svc.request_evaluation(db, user, interview_id)
