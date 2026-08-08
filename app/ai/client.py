import logging
from dataclasses import dataclass

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class AiUnavailable(Exception):
    """Raised when the assistant cannot answer. Never faked with a canned reply."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class Answer:
    text: str
    model: str


class OpenRouterClient:
    """Minimal OpenRouter chat client.

    The key lives on the server only. Browsers never see it, so usage stays
    inside our own rate limits instead of leaking to anyone with devtools.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.openrouter_api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            # OpenRouter attributes traffic with these two.
            "HTTP-Referer": self.settings.openrouter_site_url,
            "X-Title": self.settings.app_name,
        }

    async def complete(self, *, system: str, user: str, max_tokens: int = 700) -> Answer:
        if not self.enabled:
            raise AiUnavailable("assistant disabled: set OPENROUTER_API_KEY")
        payload = {
            "model": self.settings.openrouter_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            # Low temperature: this is analysis, not creative writing.
            "temperature": 0.2,
        }
        try:
            async with httpx.AsyncClient(timeout=self.settings.openrouter_timeout_seconds) as client:
                response = await client.post(
                    f"{self.settings.openrouter_base_url.rstrip('/')}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise AiUnavailable(f"assistant request failed: {exc}") from exc
        if response.status_code == 429:
            raise AiUnavailable("assistant rate limited, try again in a minute")
        if response.status_code >= 400:
            logger.warning("openrouter error", extra={"status": response.status_code})
            raise AiUnavailable(f"assistant returned {response.status_code}")
        try:
            body = response.json()
            choice = body["choices"][0]["message"]["content"]
            model = body.get("model") or self.settings.openrouter_model
        except (ValueError, KeyError, IndexError) as exc:
            raise AiUnavailable("assistant returned an unreadable response") from exc
        text = (choice or "").strip()
        if not text:
            raise AiUnavailable("assistant returned an empty answer")
        return Answer(text=text, model=model)
