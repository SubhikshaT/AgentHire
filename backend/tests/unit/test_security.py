import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.schemas.auth import RegisterRequest


def test_password_hash_is_argon2_and_verifies():
    h = hash_password("Password123")
    assert h.startswith("$argon2")
    assert h != "Password123"
    assert verify_password("Password123", h)
    assert not verify_password("wrong-password", h)


def test_verify_handles_garbage_hash():
    assert verify_password("x", "not-a-hash") is False


def test_token_roundtrip():
    uid = uuid.uuid4()
    payload = decode_access_token(create_access_token(uid, "recruiter"))
    assert payload["sub"] == str(uid)
    assert payload["role"] == "recruiter"


def test_expired_token_rejected():
    s = get_settings()
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "recruiter", "type": "access", "iat": past, "exp": past},
        s.secret_key,
        algorithm=s.jwt_algorithm,
    )
    assert decode_access_token(token) is None


def test_token_with_wrong_secret_rejected():
    token = jwt.encode({"sub": str(uuid.uuid4()), "type": "access"}, "another-secret-key-that-is-long-enough-123", algorithm="HS256")
    assert decode_access_token(token) is None


def test_register_schema_rules():
    ok = RegisterRequest(name="  Asha  ", email="A@Example.COM", password="12345678", role="candidate")
    assert ok.name == "Asha" and ok.email == "a@example.com"
    with pytest.raises(ValidationError):
        RegisterRequest(name="Asha", email="a@example.com", password="short", role="candidate")
    with pytest.raises(ValidationError):
        RegisterRequest(name="Asha", email="not-an-email", password="12345678", role="candidate")
    with pytest.raises(ValidationError):
        RegisterRequest(name="Asha", email="a@example.com", password="12345678", role="admin")
