"""Application settings, loaded from environment variables / .env file."""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "AgentHire"
    debug: bool = False

    database_url: str
    test_database_url: str | None = None

    secret_key: str = Field(min_length=16)
    access_token_minutes: int = 60
    jwt_algorithm: str = "HS256"
    auth_cookie_name: str = "agenthire_token"
    rate_limit_enabled: bool = True

    vector_backend: Literal["pgvector", "python"] = "pgvector"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    llm_provider: Literal["ollama", "gemini", "none"] = "none"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    gemini_api_key: str = ""
    gemini_model: str = ""
    llm_timeout_seconds: int = 60

    upload_dir: str = "storage/uploads"
    max_upload_size_mb: int = 10
    cors_origins: str = "http://localhost:3000"

    @field_validator("secret_key")
    @classmethod
    def secret_not_placeholder(cls, v: str) -> str:
        if v.upper().startswith("CHANGE_ME"):
            raise ValueError("SECRET_KEY is still the placeholder value; set a random secret in .env")
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        return p if p.is_absolute() else BACKEND_DIR / p

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
