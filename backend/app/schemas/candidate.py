import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import ParsingStatus, VerificationStatus


class CandidateSkillOut(BaseModel):
    id: uuid.UUID
    skill_key: str
    name: str
    category: str | None
    evidence_text: str | None
    evidence_section: str | None
    verification_status: VerificationStatus
    proficiency_level: str | None


class ResumeBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    file_type: str
    parsing_status: ParsingStatus
    parsing_error: str | None
    uploaded_at: datetime


class CandidateListItem(BaseModel):
    id: uuid.UUID
    full_name: str | None
    email: str | None
    total_experience_years: float | None
    top_skills: list[str]
    highest_education: str | None
    is_synthetic: bool
    has_account: bool
    applications: list[dict]  # [{application_id, job_id, job_title, stage, overall_score}]
    created_at: datetime


class CandidateOut(BaseModel):
    id: uuid.UUID
    full_name: str | None
    email: str | None
    phone: str | None
    professional_summary: str | None
    total_experience_years: float | None
    education: list[dict]
    work_experience: list[dict]
    projects: list[dict]
    certifications: list[dict]
    field_verification: dict
    is_synthetic: bool
    has_account: bool
    skills: list[CandidateSkillOut]
    resumes: list[ResumeBrief]
    applications: list[dict]
    created_at: datetime
    updated_at: datetime


class CandidateUpdate(BaseModel):
    """Manual corrections. Every field sent here is marked 'manually_verified'."""

    full_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    professional_summary: str | None = Field(default=None, max_length=3000)
    total_experience_years: float | None = Field(default=None, ge=0, le=60)
    education: list[dict] | None = Field(default=None, max_length=10)
    work_experience: list[dict] | None = Field(default=None, max_length=30)
    projects: list[dict] | None = Field(default=None, max_length=30)
    certifications: list[dict] | None = Field(default=None, max_length=30)


class SkillInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    evidence_text: str | None = Field(default=None, max_length=500)
    proficiency_level: str | None = Field(default=None, max_length=30)


class SkillsUpdate(BaseModel):
    """Full replacement of the skill list. Resulting skills are marked manually_verified,
    except unchanged auto-extracted ones, which keep their status and evidence."""

    skills: list[SkillInput] = Field(max_length=100)


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID | None
    original_filename: str
    file_type: str
    parsing_status: ParsingStatus
    parsing_error: str | None
    extraction_metadata: dict
    target_job_id: uuid.UUID | None
    uploaded_at: datetime
    extracted_text: str | None = None


class UploadResult(BaseModel):
    filename: str
    ok: bool
    resume_id: uuid.UUID | None = None
    candidate_id: uuid.UUID | None = None
    application_id: uuid.UUID | None = None
    error_code: str | None = None
    error: str | None = None
