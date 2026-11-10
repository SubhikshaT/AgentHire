"""Structured output of the Resume Intelligence Agent."""
from pydantic import BaseModel, Field


class ExtractedSkill(BaseModel):
    key: str                      # taxonomy key, e.g. "fastapi"
    name: str                     # display name, e.g. "FastAPI"
    matched_text: str             # exact text found in the resume
    evidence_text: str            # the line it was found in
    evidence_section: str         # resume section, e.g. "skills", "projects"


class EducationEntry(BaseModel):
    degree: str | None = None
    level: str | None = None      # phd | masters | bachelors | diploma | higher_secondary | secondary
    field: str | None = None
    institution: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    score: str | None = None
    raw_text: str


class ExperienceEntry(BaseModel):
    title: str | None = None
    company: str | None = None
    start: str | None = None      # YYYY-MM
    end: str | None = None        # YYYY-MM or "present"
    months: int | None = None
    description: str = ""
    is_internship: bool = False
    raw_text: str


class ProjectEntry(BaseModel):
    name: str
    description: str = ""
    skills: list[str] = Field(default_factory=list)


class CertificationEntry(BaseModel):
    name: str
    issuer: str | None = None
    year: int | None = None


class ParsedResume(BaseModel):
    candidate_name: str | None = None
    email: str | None = None
    phone: str | None = None
    professional_summary: str | None = None
    education: list[EducationEntry] = Field(default_factory=list)
    skills: list[ExtractedSkill] = Field(default_factory=list)
    work_experience: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    certifications: list[CertificationEntry] = Field(default_factory=list)
    total_experience_years: float | None = None
    sections_found: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
