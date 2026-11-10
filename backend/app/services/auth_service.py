"""Registration and login logic."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.models import CandidateProfile, User
from app.models.enums import Role
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.audit_service import log_action

# Used to keep login timing similar whether or not the email exists.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def link_or_create_candidate_profile(db: Session, user: User) -> CandidateProfile:
    """Link a candidate user to an existing recruiter-imported profile with the same email,
    or create an empty profile. See prompt section 5.3."""
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    if profile:
        return profile
    profile = db.scalar(
        select(CandidateProfile)
        .where(CandidateProfile.email == user.email, CandidateProfile.user_id.is_(None))
        .order_by(CandidateProfile.created_at)
        .limit(1)
    )
    if profile:
        profile.user_id = user.id
        log_action(db, user.id, "candidate_profile.linked", "candidate_profile", profile.id)
    else:
        profile = CandidateProfile(user_id=user.id, full_name=user.name, email=user.email)
        db.add(profile)
    db.flush()
    return profile


def register_user(db: Session, data: RegisterRequest) -> User:
    repo = UserRepository(db)
    if repo.get_by_email(data.email):
        raise ConflictError("An account with this email already exists.", code="email_taken")
    user = repo.add(
        User(name=data.name, email=data.email, password_hash=hash_password(data.password), role=data.role)
    )
    if data.role == Role.CANDIDATE:
        link_or_create_candidate_profile(db, user)
    log_action(db, user.id, "user.registered", "user", user.id, {"role": data.role.value})
    db.commit()
    return user


def authenticate(db: Session, data: LoginRequest) -> User:
    user = UserRepository(db).get_by_email(data.email)
    if user is None:
        verify_password(data.password, _DUMMY_HASH)
        raise UnauthorizedError("Incorrect email or password.", code="invalid_credentials")
    if not verify_password(data.password, user.password_hash):
        raise UnauthorizedError("Incorrect email or password.", code="invalid_credentials")
    if not user.is_active:
        raise UnauthorizedError("This account is disabled.", code="account_disabled")
    log_action(db, user.id, "user.login", "user", user.id)
    db.commit()
    return user
