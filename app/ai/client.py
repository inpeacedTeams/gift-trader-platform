import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

API_URL = "https://openrouter.ai/api/v1/chat/completions"


class AssistantUnavailable(Exception):
    """The assistant cannot answer. Surfaced to the user, never swallowed."""


@dataclass(frozen=True)
class Answer:
    text: str
    model: str


class OpenRouterClient:
    """Thin wrapper over the OpenRouter chat API.

    The key lives on the server only. Browsers talk to our endpoints, never
    to OpenRouter, so the key is never shipped to a client.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    @property
    def configured(self) -> bool:
        return bool(self.settings.openrouter_api_key)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        if self.settings.openrouter_site_url:
            headers["HTTP-Referer"] = self.settings.openrouter_site_url
        headers["X-Title"] = self.settings.app_name
        return headers

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 700,
        temperature: float = 0.2,
    ) -> Answer:
        if not self.configured:
            raise AssistantUnavailable(
                "AI assistant is not configured: set OPENROUTER_API_KEY"
            )
        payload: dict[str, Any] = {
            "model": self.settings.openrouter_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            async with httpx.AsyncClient(timeout=self.settings.openrouter_timeout_seconds) as client:
                response = await client.post(API_URL, headers=self._headers(), json=payload)
        except httpx.HTTPError as exc:
            raise AssistantUnavailable(f"assistant request failed: {exc}") from exc
        if response.status_code == 429:
            raise AssistantUnavailable("assistant is rate limited, try again shortly")
        if response.status_code >= 400:
            logger.warning(
                "openrouter rejected the request",
                extra={"status": response.status_code, "body": response.text[:400]},
            )
            raise AssistantUnavailable(f"assistant returned {response.status_code}")
        try:
            body = response.json()
            choice = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError) as exc:
            raise AssistantUnavailable("assistant returned an unreadable response") from exc
        text = (choice or "").strip()
        if not text:
            raise AssistantUnavailable("assistant returned an empty answer")
        return Answer(text=text, model=body.get("model") or self.settings.openrouter_model)
