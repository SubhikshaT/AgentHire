"""Per-recruiter matching and rubric weights."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.agents.matching_agent import DEFAULT_WEIGHTS, validate_weights
from app.ai.rubric import DEFAULT_RUBRIC_WEIGHTS, validate_rubric_weights
from app.core.exceptions import AppError
from app.models import AppSettings, User
from app.services.audit_service import log_action


def get_settings_row(db: Session, user: User) -> AppSettings | None:
    return db.scalar(select(AppSettings).where(AppSettings.recruiter_id == user.id))


def matching_weights(db: Session, recruiter_id) -> dict:
    row = db.scalar(select(AppSettings).where(AppSettings.recruiter_id == recruiter_id))
    return dict(row.matching_weights) if row else dict(DEFAULT_WEIGHTS)


def rubric_weights(db: Session, recruiter_id) -> dict:
    row = db.scalar(select(AppSettings).where(AppSettings.recruiter_id == recruiter_id))
    return dict(row.rubric_weights) if row else dict(DEFAULT_RUBRIC_WEIGHTS)


def _row(db: Session, user: User) -> AppSettings:
    row = get_settings_row(db, user)
    if row is None:
        row = AppSettings(recruiter_id=user.id, matching_weights=dict(DEFAULT_WEIGHTS),
                          rubric_weights=dict(DEFAULT_RUBRIC_WEIGHTS))
        db.add(row)
    return row


def set_matching_weights(db: Session, user: User, weights: dict) -> dict:
    try:
        clean = validate_weights(weights)
    except ValueError as e:
        raise AppError(str(e), code="invalid_weights", status_code=422) from None
    row = _row(db, user)
    row.matching_weights = clean
    log_action(db, user.id, "settings.matching_weights", "app_settings", None, clean)
    db.commit()
    return clean


def set_rubric_weights(db: Session, user: User, weights: dict) -> dict:
    try:
        clean = validate_rubric_weights(weights)
    except ValueError as e:
        raise AppError(str(e), code="invalid_weights", status_code=422) from None
    row = _row(db, user)
    row.rubric_weights = clean
    log_action(db, user.id, "settings.rubric_weights", "app_settings", None, clean)
    db.commit()
    return clean
