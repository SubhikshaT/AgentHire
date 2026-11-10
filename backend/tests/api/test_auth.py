from sqlalchemy import select

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.models import AuditLog, CandidateProfile, User
from helpers import register

COOKIE = get_settings().auth_cookie_name


def test_register_sets_httponly_cookie_and_hides_hash(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"name": "Rita", "email": "Rita@Example.com", "password": "Password123", "role": "recruiter"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "rita@example.com"
    assert body["role"] == "recruiter"
    assert "password_hash" not in body and "password" not in body
    set_cookie = r.headers["set-cookie"]
    assert COOKIE in set_cookie and "HttpOnly" in set_cookie and "SameSite=lax" in set_cookie


def test_register_duplicate_email_conflict(client):
    register(client, email="dup@example.com")
    r = client.post(
        "/api/v1/auth/register",
        json={"name": "Other", "email": "DUP@example.com", "password": "Password123", "role": "candidate"},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "email_taken"


def test_register_validation_error_format(client):
    r = client.post(
        "/api/v1/auth/register", json={"name": "A", "email": "bad", "password": "x", "role": "admin"}
    )
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "validation_error"
    fields = {d["field"] for d in err["details"]}
    assert {"name", "email", "password", "role"} <= fields


def test_register_malformed_json(client):
    r = client.post(
        "/api/v1/auth/register", content="{not json", headers={"Content-Type": "application/json"}
    )
    assert r.status_code == 422


def test_password_stored_hashed(client, db):
    register(client, email="h@example.com")
    user = db.scalar(select(User).where(User.email == "h@example.com"))
    assert user.password_hash.startswith("$argon2")


def test_login_me_logout_flow(make_client):
    c = make_client()
    register(c, email="flow@example.com")
    c.cookies.clear()

    assert c.get("/api/v1/auth/me").status_code == 401

    r = c.post("/api/v1/auth/login", json={"email": "FLOW@example.com", "password": "Password123"})
    assert r.status_code == 200
    me = c.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["email"] == "flow@example.com"

    out = c.post("/api/v1/auth/logout")
    assert out.status_code == 204
    assert c.get("/api/v1/auth/me").status_code == 401


def test_login_wrong_password_and_unknown_email_same_error(client):
    register(client, email="x@example.com")
    a = client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "nope-nope"})
    b = client.post("/api/v1/auth/login", json={"email": "ghost@example.com", "password": "nope-nope"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()
    assert a.json()["error"]["code"] == "invalid_credentials"


def test_disabled_user_cannot_login_or_use_token(client, db):
    register(client, email="off@example.com")
    user = db.scalar(select(User).where(User.email == "off@example.com"))
    user.is_active = False
    db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401
    r = client.post("/api/v1/auth/login", json={"email": "off@example.com", "password": "Password123"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "account_disabled"


def test_tampered_token_rejected(client):
    register(client, email="t@example.com")
    client.cookies.clear()
    client.cookies.set(COOKIE, "abc.def.ghi")
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_token"


def test_candidate_registration_creates_profile(client, db):
    u = register(client, role="candidate", email="cand@example.com", name="Cand One")
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == u["id"]))
    assert profile is not None and profile.email == "cand@example.com"


def test_recruiter_registration_creates_no_profile(client, db):
    register(client, role="recruiter", email="rec@example.com")
    assert db.scalar(select(CandidateProfile)) is None


def test_candidate_registration_links_existing_imported_profile(client, db):
    imported = CandidateProfile(full_name="Imported Person", email="link@example.com")
    db.add(imported)
    db.commit()
    u = register(client, role="candidate", email="LINK@example.com")
    db.expire_all()
    profiles = db.scalars(select(CandidateProfile)).all()
    assert len(profiles) == 1
    assert str(profiles[0].user_id) == u["id"]
    assert profiles[0].full_name == "Imported Person"


def test_audit_log_written(client, db):
    register(client, email="audit@example.com")
    client.post("/api/v1/auth/login", json={"email": "audit@example.com", "password": "Password123"})
    actions = {a.action for a in db.scalars(select(AuditLog)).all()}
    assert {"user.registered", "user.login"} <= actions


def test_login_rate_limited(client):
    limiter.enabled = True
    limiter.reset()
    try:
        codes = [
            client.post("/api/v1/auth/login", json={"email": "r@example.com", "password": "wrong-pass"}).status_code
            for _ in range(12)
        ]
    finally:
        limiter.enabled = False
        limiter.reset()
    assert 429 in codes
    assert codes[:10] == [401] * 10


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["database"] == "ok"
