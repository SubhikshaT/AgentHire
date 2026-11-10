"""Local LLM through Ollama (http://localhost:11434). Free, runs on your machine."""
import httpx

from app.ai.providers.base import LLMProvider, LLMUnavailable
from app.core.config import get_settings


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self):
        s = get_settings()
        self.base = s.ollama_base_url.rstrip("/")
        self.model_id = s.ollama_model

    def is_configured(self) -> bool:
        return bool(self.base and self.model_id)

    def ping(self) -> bool:
        try:
            r = httpx.get(f"{self.base}/api/tags", timeout=3)
            if r.status_code != 200:
                return False
            names = {m.get("name") for m in r.json().get("models", [])}
            return self.model_id in names or f"{self.model_id}:latest" in names
        except httpx.HTTPError:
            return False

    def _complete(self, system: str, user: str, schema: dict, timeout: float) -> str:
        try:
            r = httpx.post(
                f"{self.base}/api/chat",
                json={
                    "model": self.model_id,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "format": schema,
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
                timeout=timeout,
            )
        except httpx.TimeoutException as e:
            raise LLMUnavailable(f"Ollama did not answer within {timeout:.0f}s.") from e
        except httpx.HTTPError as e:
            raise LLMUnavailable(f"Cannot reach Ollama at {self.base}. Is `ollama serve` running?") from e
        if r.status_code == 404:
            raise LLMUnavailable(f"Ollama model '{self.model_id}' not found. Run: ollama pull {self.model_id}")
        if r.status_code != 200:
            raise LLMUnavailable(f"Ollama error {r.status_code}.")
        return r.json().get("message", {}).get("content", "")
