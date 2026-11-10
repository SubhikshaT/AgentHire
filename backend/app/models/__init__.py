"""Import all models so Alembic and relationships can see them."""
from app.models.candidate import CandidateProfile, CandidateSkill, Resume, ResumeChunk, Skill
from app.models.interview import Interview, InterviewAnswer, InterviewQuestion
from app.models.job import Application, CandidateMatch, Job, StageHistory
from app.models.report import (
    AIAuditLog,
    AppSettings,
    AuditLog,
    EvaluationReport,
    LearningProgress,
    RecruiterNote,
)
from app.models.user import User

__all__ = [
    "User",
    "CandidateProfile",
    "Resume",
    "ResumeChunk",
    "Skill",
    "CandidateSkill",
    "Job",
    "Application",
    "StageHistory",
    "CandidateMatch",
    "Interview",
    "InterviewQuestion",
    "InterviewAnswer",
    "EvaluationReport",
    "RecruiterNote",
    "AIAuditLog",
    "AuditLog",
    "AppSettings",
    "LearningProgress",
]
