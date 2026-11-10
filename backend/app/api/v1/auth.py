from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import AUTH_LIMIT, limiter
from app.core.security import create_access_token
from app.database.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookie(response: Response, user: User) -> None:
    s = get_settings()
    response.set_cookie(
        key=s.auth_cookie_name,
        value=create_access_token(user.id, user.role),
        max_age=s.access_token_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=not s.debug,
        path="/",
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(AUTH_LIMIT)
def register(request: Request, response: Response, data: RegisterRequest, db: Session = Depends(get_db)):
    user = auth_service.register_user(db, data)
    _set_auth_cookie(response, user)
    return user


@router.post("/login", response_model=UserOut)
@limiter.limit(AUTH_LIMIT)
def login(request: Request, response: Response, data: LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, data)
    _set_auth_cookie(response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def logout():
    s = get_settings()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(s.auth_cookie_name, path="/", httponly=True, samesite="lax", secure=not s.debug)
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
