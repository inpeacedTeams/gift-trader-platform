import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

CHAT_PATH = "/chat/completions"


class OpenRouterError(Exception):
    """The assistant could not answer. Carries a message safe to show a user."""


class OpenRouterClient:
    """Minimal OpenRouter client.

    OpenRouter speaks the OpenAI chat format, so this stays deliberately thin:
    one request, one answer, no streaming and no SDK dependency.
    """

    def __init__(
        self,
        api_key: str | None,
        *,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "openrouter/free",
        timeout: float = 45.0,
        app_url: str = "https://github.com/inpeacedTeams/gift-trader-platform",
        app_title: str = "Gift Trader",
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.app_url = app_url
        self.app_title = app_title

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # OpenRouter uses these for attribution on its dashboard.
            "HTTP-Referer": self.app_url,
            "X-Title": self.app_title,
        }

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 700,
        temperature: float = 0.2,
    ) -> str:
        if not self.configured:
            raise OpenRouterError("AI assistant is not configured on this server")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            # Low temperature: this is analysis over real numbers, not creative writing.
            "temperature": temperature,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{CHAT_PATH}", headers=self._headers(), json=payload
                )
        except httpx.HTTPError as exc:
            logger.warning("openrouter request failed", exc_info=exc)
            raise OpenRouterError("AI provider is unreachable right now") from exc
        if response.status_code == 429:
            raise OpenRouterError("AI rate limit reached, try again in a minute")
        if response.status_code >= 400:
            logger.warning(
                "openrouter rejected the request",
                extra={"status": response.status_code, "body": response.text[:400]},
            )
            raise OpenRouterError("AI provider rejected the request")
        try:
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except (ValueError, KeyError, IndexError, AttributeError) as exc:
            raise OpenRouterError("AI returned an unreadable answer") from exc
