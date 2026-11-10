import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ApplicationSource, Stage


class ApplicationOut(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    job_title: str
    candidate_name: str | None
    candidate_email: str | None
    stage: Stage
    source: ApplicationSource
    created_at: datetime
    overall_score: float | None = None
    match_id: uuid.UUID | None = None
    resume_status: str | None = None
    is_synthetic: bool = False


class StageChange(BaseModel):
    stage: Stage
    note: str | None = Field(default=None, max_length=1000)


class StageHistoryOut(BaseModel):
    id: uuid.UUID
    from_stage: Stage | None
    to_stage: Stage
    changed_by: uuid.UUID | None
    changed_by_name: str | None
    changed_at: datetime
    note: str | None
