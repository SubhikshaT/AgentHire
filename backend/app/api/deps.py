"""Shared FastAPI dependencies: DB session, current user, role guards."""
import uuid
from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models import User
from app.models.enums import Role


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(get_settings().auth_cookie_name)
    if not token:
        raise UnauthorizedError("Please log in.", code="not_authenticated")
    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedError("Your session has expired. Please log in again.", code="invalid_token")
    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError:
        raise UnauthorizedError("Invalid session.", code="invalid_token") from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Account not found or disabled.", code="invalid_token")
    return user


def require_role(*roles: Role) -> Callable[..., User]:
    allowed = {r.value for r in roles}

    def guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise ForbiddenError("You do not have permission for this action.")
        return user

    return guard


require_recruiter = require_role(Role.RECRUITER)
require_candidate = require_role(Role.CANDIDATE)
