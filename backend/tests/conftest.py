"""Test setup: runs against a real PostgreSQL test database (TEST_DATABASE_URL).

The test DB is migrated with Alembic at session start and all tables are
truncated after every test.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv_loader import load_test_env  # noqa: E402  (local helper, see tests/dotenv_loader.py)

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_test_env(BACKEND_DIR)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.rate_limit import limiter  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from helpers import register  # noqa: E402,F401


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    env = {**os.environ, "ALEMBIC_DATABASE_URL": os.environ["DATABASE_URL"]}
    alembic = [sys.executable, "-m", "alembic"]
    for args in (["downgrade", "base"], ["upgrade", "head"]):
        subprocess.run(alembic + args, cwd=BACKEND_DIR, env=env, check=True, capture_output=True)
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    names = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    limiter.enabled = False
    with TestClient(app) as c:
        yield c


@pytest.fixture
def make_client():
    """Factory for extra independent clients (separate cookie jars = separate users)."""
    clients = []

    def _make():
        c = TestClient(app)
        c.__enter__()
        clients.append(c)
        return c

    yield _make
    for c in clients:
        c.__exit__(None, None, None)
