"""Writes user-action audit entries (who did what to which record)."""
import uuid

from sqlalchemy.orm import Session

from app.models import AuditLog


def log_action(
    db: Session,
    user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    meta: dict | None = None,
) -> None:
    db.add(AuditLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, meta=meta or {}))
