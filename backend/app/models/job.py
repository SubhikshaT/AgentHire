import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, Timestamps, UUIDPk, embedding_type, utcnow
from app.models.enums import ApplicationSource, JobStatus, Stage, check_in


class Job(UUIDPk, Timestamps, Base):
    __tablename__ = "jobs"
    __table_args__ = (CheckConstraint(check_in("status", JobStatus), name="status_valid"),)

    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    department: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    required_skills: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    preferred_skills: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    minimum_experience: Mapped[float | None] = mapped_column(Float)
    education_requirements: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    certifications: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    responsibilities: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    soft_skills: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=JobStatus.DRAFT, index=True, nullable=False)
    analysis_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    embedding = mapped_column(embedding_type(), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(120))

    applications: Mapped[list["Application"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", passive_deletes=True
    )


class Application(UUIDPk, Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_application_candidate_job"),
        CheckConstraint(check_in("stage", Stage), name="stage_valid"),
        CheckConstraint(check_in("source", ApplicationSource), name="source_valid"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    stage: Mapped[str] = mapped_column(String(30), default=Stage.APPLIED, index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    job: Mapped[Job] = relationship(back_populates="applications")
    candidate = relationship("CandidateProfile")
    history: Mapped[list["StageHistory"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="StageHistory.changed_at",
    )


class StageHistory(UUIDPk, Base):
    __tablename__ = "stage_history"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    from_stage: Mapped[str | None] = mapped_column(String(30))
    to_stage: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    application: Mapped[Application] = relationship(back_populates="history")


class CandidateMatch(UUIDPk, Base):
    __tablename__ = "candidate_matches"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    semantic_score: Mapped[float] = mapped_column(Float, nullable=False)
    required_skill_score: Mapped[float] = mapped_column(Float, nullable=False)
    preferred_skill_score: Mapped[float] = mapped_column(Float, nullable=False)
    experience_score: Mapped[float] = mapped_column(Float, nullable=False)
    education_score: Mapped[float] = mapped_column(Float, nullable=False)
    certification_score: Mapped[float] = mapped_column(Float, nullable=False)
    keyword_baseline_score: Mapped[float] = mapped_column(Float, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    weights_used: Mapped[dict] = mapped_column(JSONB, nullable=False)
    explanation: Mapped[dict] = mapped_column(JSONB, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    application: Mapped[Application] = relationship()
