"""Allowed values for status-like columns. Stored as strings with CHECK constraints."""
from enum import StrEnum


class Role(StrEnum):
    RECRUITER = "recruiter"
    CANDIDATE = "candidate"


class ParsingStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VerificationStatus(StrEnum):
    AUTO_EXTRACTED = "auto_extracted"
    MANUALLY_VERIFIED = "manually_verified"


class JobStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class Stage(StrEnum):
    APPLIED = "applied"
    RESUME_REVIEWED = "resume_reviewed"
    SHORTLISTED = "shortlisted"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    UNDER_REVIEW = "under_review"
    SELECTED = "selected"
    REJECTED = "rejected"


class ApplicationSource(StrEnum):
    CANDIDATE_APPLIED = "candidate_applied"
    RECRUITER_UPLOAD = "recruiter_upload"


class InterviewType(StrEnum):
    ASSIGNED = "assigned"
    PRACTICE = "practice"


class InterviewStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class QuestionSource(StrEnum):
    LLM = "llm"
    QUESTION_BANK = "question_bank"
    RECRUITER = "recruiter"


class Verdict(StrEnum):
    CORRECT = "correct"
    PARTIALLY_CORRECT = "partially_correct"
    INCORRECT = "incorrect"
    INSUFFICIENT = "insufficient"


class EvaluationStatus(StrEnum):
    NOT_SUBMITTED = "not_submitted"
    PENDING_LLM = "pending_llm"
    EVALUATED = "evaluated"
    FAILED = "failed"


def check_in(column: str, enum_cls) -> str:
    values = ", ".join(f"'{v.value}'" for v in enum_cls)
    return f"{column} IN ({values})"
