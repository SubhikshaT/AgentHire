"""Provider selection from LLM_PROVIDER (ollama | gemini | none).

Tests replace the provider with `set_provider_override(FakeProvider(...))`.
"""
import time

from app.ai.providers.base import LLMProvider, LLMUnavailable
from app.core.config import get_settings


class NoProvider(LLMProvider):
    name = "none"
    model_id = None

    def is_configured(self) -> bool:
        return False

    def _complete(self, system, user, schema, timeout):
        raise LLMUnavailable("No LLM provider is configured (LLM_PROVIDER=none).")


_override: LLMProvider | None = None
_status_cache: dict = {"t": 0.0, "val": None}


def set_provider_override(p: LLMProvider | None) -> None:
    global _override
    _override = p
    _status_cache["t"] = 0.0


def get_provider() -> LLMProvider:
    if _override is not None:
        return _override
    kind = get_settings().llm_provider
    if kind == "ollama":
        from app.ai.providers.ollama import OllamaProvider

        return OllamaProvider()
    if kind == "gemini":
        from app.ai.providers.gemini import GeminiProvider

        return GeminiProvider()
    return NoProvider()


def llm_available() -> bool:
    return bool(llm_status()["available"])


def llm_status() -> dict:
    now = time.monotonic()
    if _status_cache["val"] is not None and now - _status_cache["t"] < 30:
        return _status_cache["val"]
    p = get_provider()
    configured = p.is_configured()
    reachable = p.ping() if configured else False
    val = {
        "provider": p.name,
        "model": p.model_id,
        "configured": configured,
        "available": configured and reachable,
        "sends_data_externally": p.name == "gemini",
        "message": (
            "LLM is ready." if configured and reachable else
            "No LLM configured. Matching, parsing and question-bank interviews work; "
            "AI answer evaluation is pending until an LLM is configured." if not configured else
            f"{p.name} is configured but not reachable. Check that it is running."
        ),
    }
    _status_cache.update(t=now, val=val)
    return val
