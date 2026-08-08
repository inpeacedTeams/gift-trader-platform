import logging
from dataclasses import dataclass

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class AiUnavailable(Exception):
    """Raised when the assistant cannot answer, with a reason worth showing."""


@dataclass(frozen=True)
class AiReply:
    content: str
    model: str


class OpenRouterClient:
    """Minimal OpenRouter caller.

    The API is OpenAI compatible, so a single POST is enough and pulling a
    whole SDK in would only add weight.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    @property
    def configured(self) -> bool:
        return bool(self.settings.openrouter_api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            # OpenRouter uses these for attribution on the dashboard.
            "HTTP-Referer": self.settings.openrouter_site_url,
            "X-Title": self.settings.app_name,
        }

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 700,
        temperature: float = 0.2,
    ) -> AiReply:
        if not self.configured:
            raise AiUnavailable("AI is not configured: set OPENROUTER_API_KEY")
        payload = {
            "model": self.settings.openrouter_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        url = f"{self.settings.openrouter_base_url.rstrip('/')}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=self.settings.ai_timeout_seconds) as client:
                response = await client.post(url, headers=self._headers(), json=payload)
        except httpx.HTTPError as exc:
            raise AiUnavailable(f"OpenRouter request failed: {exc}") from exc
        if response.status_code == 401:
            raise AiUnavailable("OpenRouter rejected the API key")
        if response.status_code == 429:
            raise AiUnavailable("OpenRouter rate limit reached, try again shortly")
        if response.status_code >= 400:
            raise AiUnavailable(f"OpenRouter returned {response.status_code}")
        try:
            body = response.json()
            choice = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError) as exc:
            raise AiUnavailable("OpenRouter returned an unexpected response") from exc
        content = (choice or "").strip()
        if not content:
            raise AiUnavailable("The model returned an empty answer")
        return AiReply(content=content, model=body.get("model", self.settings.openrouter_model))
