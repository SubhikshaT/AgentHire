"""Point the app at the test database before any app module is imported."""
import os
from pathlib import Path


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        values[k.strip()] = v.strip()
    return values


def load_test_env(backend_dir: Path) -> None:
    if os.environ.get("AGENTHIRE_TEST_ENV_LOADED") == "1":
        return
    file_values = _read_env_file(backend_dir / ".env")
    test_url = os.environ.get("TEST_DATABASE_URL") or file_values.get("TEST_DATABASE_URL")
    if not test_url:
        raise RuntimeError("TEST_DATABASE_URL is not set. Add it to backend/.env (see .env.example).")
    if test_url == (os.environ.get("DATABASE_URL") or file_values.get("DATABASE_URL")):
        raise RuntimeError("TEST_DATABASE_URL must be different from DATABASE_URL (tests wipe the database).")
    os.environ["DATABASE_URL"] = test_url
    os.environ["AGENTHIRE_TEST_ENV_LOADED"] = "1"
    os.environ["DEBUG"] = "true"
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    os.environ.setdefault("LLM_PROVIDER", "none")
    import tempfile
    os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="agenthire-test-uploads-")
