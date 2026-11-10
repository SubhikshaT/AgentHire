import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import JobStatus

EDU_LEVELS = {"phd", "masters", "bachelors", "diploma", "higher_secondary", "secondary"}


def _clean_list(v: list[str]) -> list[str]:
    out: list[str] = []
    for s in v or []:
        s = (s or "").strip()
        if s and s.lower() not in {x.lower() for x in out}:
            out.append(s[:120])
    return out


class EducationRequirement(BaseModel):
    level: str
    fields: list[str] = Field(default_factory=list)

    @field_validator("level")
    @classmethod
    def valid_level(cls, v: str) -> str:
        if v not in EDU_LEVELS:
            raise ValueError(f"level must be one of {sorted(EDU_LEVELS)}")
        return v


class JobBase(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    department: str | None = Field(default=None, max_length=120)
    description: str = Field(default="", max_length=20000)
    required_skills: list[str] = Field(default_factory=list, max_length=60)
    preferred_skills: list[str] = Field(default_factory=list, max_length=60)
    soft_skills: list[str] = Field(default_factory=list, max_length=30)
    minimum_experience: float | None = Field(default=None, ge=0, le=40)
    education_requirements: list[EducationRequirement] = Field(default_factory=list, max_length=5)
    certifications: list[str] = Field(default_factory=list, max_length=20)
    responsibilities: list[str] = Field(default_factory=list, max_length=40)

    @field_validator("required_skills", "preferred_skills", "soft_skills", "certifications", "responsibilities")
    @classmethod
    def _clean(cls, v: list[str]) -> list[str]:
        return _clean_list(v)

    @field_validator("title")
    @classmethod
    def _strip_title(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Title must have at least 2 characters")
        return v


class JobCreate(JobBase):
    analyze: bool = False  # if true, fill empty structured fields from the description


class JobUpdate(JobBase):
    pass


class JobOut(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recruiter_id: uuid.UUID
    status: JobStatus
    is_synthetic: bool
    analysis_metadata: dict
    created_at: datetime
    updated_at: datetime
    applicant_count: int = 0


class JobAnalyzeRequest(BaseModel):
    description: str | None = Field(default=None, max_length=20000)
    apply: bool = False  # true = save the extracted fields onto the job
