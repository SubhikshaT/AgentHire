"""Rate limiter (slowapi) keyed by client IP."""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

limiter = Limiter(key_func=get_remote_address, enabled=get_settings().rate_limit_enabled)

AUTH_LIMIT = "10/minute"
UPLOAD_LIMIT = "30/minute"
LLM_LIMIT = "20/minute"
