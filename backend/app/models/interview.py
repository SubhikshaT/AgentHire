import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, Timestamps, UUIDPk, utcnow
from app.models.enums import (
    EvaluationStatus,
    InterviewStatus,
    InterviewType,
    QuestionSource,
    check_in,
)


class Interview(UUIDPk, Timestamps, Base):
    __tablename__ = "interviews"
    __table_args__ = (
        CheckConstraint(check_in("interview_type", InterviewType), name="type_valid"),
        CheckConstraint(check_in("status", InterviewStatus), name="status_valid"),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    interview_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=InterviewStatus.DRAFT, index=True, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    categories: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_score: Mapped[float | None] = mapped_column(Float)

    application = relationship("Application")
    questions: Mapped[list["InterviewQuestion"]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="InterviewQuestion.sequence_number",
    )


class InterviewQuestion(UUIDPk, Base):
    __tablename__ = "interview_questions"
    __table_args__ = (CheckConstraint(check_in("source", QuestionSource), name="source_valid"),)

    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    expected_concepts: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    evaluation_rubric: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    time_limit_seconds: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    grounding: Mapped[str | None] = mapped_column(Text)
    sequence_number: Mapped[float] = mapped_column(Float, nullable=False)
    parent_question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interview_questions.id", ondelete="CASCADE"), nullable=True
    )

    interview: Mapped[Interview] = relationship(back_populates="questions")
    answer: Mapped["InterviewAnswer | None"] = relationship(
        back_populates="question", uselist=False, cascade="all, delete-orphan", passive_deletes=True
    )


class InterviewAnswer(UUIDPk, Base):
    __tablename__ = "interview_answers"
    __table_args__ = (
        CheckConstraint(check_in("evaluation_status", EvaluationStatus), name="eval_status_valid"),
    )

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    answer_text: Mapped[str | None] = mapped_column(Text)
    draft_text: Mapped[str | None] = mapped_column(Text)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    technical_score: Mapped[float | None] = mapped_column(Float)
    conceptual_score: Mapped[float | None] = mapped_column(Float)
    problem_solving_score: Mapped[float | None] = mapped_column(Float)
    clarity_score: Mapped[float | None] = mapped_column(Float)
    relevance_score: Mapped[float | None] = mapped_column(Float)
    weighted_score: Mapped[float | None] = mapped_column(Float)
    verdict: Mapped[str | None] = mapped_column(String(30))
    feedback: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    concept_coverage: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    evaluation_status: Mapped[str] = mapped_column(
        String(20), default=EvaluationStatus.NOT_SUBMITTED, nullable=False
    )
    served_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    draft_saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    question: Mapped[InterviewQuestion] = relationship(back_populates="answer")
