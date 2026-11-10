import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPk, utcnow


class EvaluationReport(UUIDPk, Base):
    __tablename__ = "evaluation_reports"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    interview_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="SET NULL"), nullable=True
    )
    report_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    report_file_path: Mapped[str | None] = mapped_column(Text)
    methodology_version: Mapped[str] = mapped_column(String(40), nullable=False)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    notes: Mapped[list["RecruiterNote"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", passive_deletes=True,
        order_by="RecruiterNote.created_at",
    )


class RecruiterNote(UUIDPk, Base):
    __tablename__ = "recruiter_notes"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_reports.id", ondelete="CASCADE"), index=True, nullable=False
    )
    recruiter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    report: Mapped[EvaluationReport] = relationship(back_populates="notes")


class AIAuditLog(UUIDPk, Base):
    __tablename__ = "ai_audit_logs"

    agent: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    model_id: Mapped[str | None] = mapped_column(String(120))
    prompt_version: Mapped[str | None] = mapped_column(String(40))
    rubric_version: Mapped[str | None] = mapped_column(String(40))
    input_refs: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    output_ref_type: Mapped[str | None] = mapped_column(String(60))
    output_ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    validation_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    human_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuditLog(UUIDPk, Base):
    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True, nullable=False
    )


class AppSettings(UUIDPk, Base):
    __tablename__ = "app_settings"

    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    matching_weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    rubric_weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class LearningProgress(UUIDPk, Base):
    __tablename__ = "learning_progress"
    __table_args__ = (UniqueConstraint("candidate_id", "resource_key", name="uq_learning_progress"),)

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resource_key: Mapped[str] = mapped_column(String(120), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
