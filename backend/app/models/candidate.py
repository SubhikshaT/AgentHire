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
from app.models.enums import ParsingStatus, VerificationStatus, check_in


class CandidateProfile(UUIDPk, Timestamps, Base):
    __tablename__ = "candidate_profiles"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    full_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    professional_summary: Mapped[str | None] = mapped_column(Text)
    total_experience_years: Mapped[float | None] = mapped_column(Float)
    education: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    work_experience: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    projects: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    certifications: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # Which top-level fields a human has confirmed or corrected, e.g. {"education": "manually_verified"}
    field_verification: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", passive_deletes=True
    )
    skills: Mapped[list["CandidateSkill"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", passive_deletes=True
    )


class Resume(UUIDPk, Base):
    __tablename__ = "resumes"
    __table_args__ = (CheckConstraint(check_in("parsing_status", ParsingStatus), name="parsing_status_valid"),)

    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    parsing_status: Mapped[str] = mapped_column(String(20), default=ParsingStatus.PENDING, nullable=False)
    parsing_error: Mapped[str | None] = mapped_column(Text)
    extraction_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    target_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    candidate: Mapped[CandidateProfile | None] = relationship(back_populates="resumes")
    chunks: Mapped[list["ResumeChunk"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", passive_deletes=True
    )


class ResumeChunk(UUIDPk, Base):
    __tablename__ = "resume_chunks"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    section: Mapped[str] = mapped_column(String(50), nullable=False)
    chunk_index: Mapped[int] = mapped_column(nullable=False, default=0)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(embedding_type(), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    resume: Mapped[Resume] = relationship(back_populates="chunks")


class Skill(UUIDPk, Base):
    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(Text)


class CandidateSkill(UUIDPk, Base):
    __tablename__ = "candidate_skills"
    __table_args__ = (
        UniqueConstraint("candidate_id", "skill_id", name="uq_candidate_skill"),
        CheckConstraint(check_in("verification_status", VerificationStatus), name="verification_valid"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    proficiency_level: Mapped[str | None] = mapped_column(String(30))
    evidence_text: Mapped[str | None] = mapped_column(Text)
    evidence_section: Mapped[str | None] = mapped_column(String(50))
    verification_status: Mapped[str] = mapped_column(
        String(30), default=VerificationStatus.AUTO_EXTRACTED, nullable=False
    )

    candidate: Mapped[CandidateProfile] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship()
