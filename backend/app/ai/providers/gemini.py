"""Google Gemini API (optional). The key stays in backend/.env and is sent only to Google."""
import httpx

from app.ai.providers.base import LLMProvider, LLMUnavailable
from app.core.config import get_settings

API = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self):
        s = get_settings()
        self.key = s.gemini_api_key
        self.model_id = s.gemini_model

    def is_configured(self) -> bool:
        return bool(self.key and self.model_id)

    def ping(self) -> bool:
        if not self.is_configured():
            return False
        try:
            r = httpx.get(f"{API}/{self.model_id}", headers={"x-goog-api-key": self.key}, timeout=5)
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    def _complete(self, system: str, user: str, schema: dict, timeout: float) -> str:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        }
        try:
            r = httpx.post(f"{API}/{self.model_id}:generateContent", json=body,
                           headers={"x-goog-api-key": self.key}, timeout=timeout)
        except httpx.TimeoutException as e:
            raise LLMUnavailable(f"Gemini did not answer within {timeout:.0f}s.") from e
        except httpx.HTTPError as e:
            raise LLMUnavailable("Cannot reach the Gemini API.") from e
        if r.status_code in (401, 403):
            raise LLMUnavailable("Gemini rejected the API key.")
        if r.status_code == 429:
            raise LLMUnavailable("Gemini rate limit reached. Try again later.")
        if r.status_code != 200:
            raise LLMUnavailable(f"Gemini error {r.status_code}.")
        try:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, ValueError):
            return ""
