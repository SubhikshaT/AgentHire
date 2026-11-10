"""Records every AI generation (provider, model, prompt/rubric version, inputs, timing, validation)."""
import uuid

from sqlalchemy.orm import Session

from app.models import AIAuditLog


def record(db: Session, *, agent: str, provider: str, model_id: str | None, prompt_version: str | None,
           rubric_version: str | None = None, input_refs: dict | None = None, output_ref_type: str | None = None,
           output_ref_id: uuid.UUID | None = None, duration_ms: int | None = None, validation_passed: bool,
           retry_count: int = 0, error_message: str | None = None, human_edited: bool = False) -> AIAuditLog:
    row = AIAuditLog(agent=agent, provider=provider, model_id=model_id, prompt_version=prompt_version,
                     rubric_version=rubric_version, input_refs={k: str(v) for k, v in (input_refs or {}).items()},
                     output_ref_type=output_ref_type, output_ref_id=output_ref_id, duration_ms=duration_ms,
                     validation_passed=validation_passed, retry_count=retry_count,
                     error_message=(error_message or None) and error_message[:1000], human_edited=human_edited)
    db.add(row)
    return row
