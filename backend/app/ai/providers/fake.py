"""TEST DOUBLE ONLY. A fake LLM provider that returns pre-written JSON.

Used by automated tests so they do not depend on Ollama or Gemini. It is never
selected by configuration; tests install it with set_provider_override().
"""
from collections.abc import Callable

from app.ai.providers.base import LLMProvider


class FakeProvider(LLMProvider):
    name = "fake-test-double"
    model_id = "fake-model"

    def __init__(self, responder: Callable[[str, str, dict], str]):
        """responder(system, user, schema) -> raw text the 'model' returns."""
        self.responder = responder
        self.calls: list[dict] = []

    def is_configured(self) -> bool:
        return True

    def ping(self) -> bool:
        return True

    def _complete(self, system: str, user: str, schema: dict, timeout: float) -> str:
        self.calls.append({"system": system, "user": user})
        return self.responder(system, user, schema)
