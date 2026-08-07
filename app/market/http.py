import asyncio
from typing import Any
import httpx
from .models import SourceUnavailable

class MarketHttp:
    def __init__(self, timeout: float = 20.0, retries: int = 2, backoff_seconds: float = 0.5, user_agent: str = "GiftTrader/0.1"):
        self.timeout = timeout
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.user_agent = user_agent

    async def _request(self, marketplace: str, method: str, url: str, *, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None) -> httpx.Response:
        request_headers = {"User-Agent": self.user_agent, "Accept": "application/json", **(headers or {})}
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    response = await client.request(method, url, headers=request_headers, params=params)
                    response.raise_for_status()
                    return response
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < self.retries:
                    await asyncio.sleep(self.backoff_seconds * (2 ** attempt))
        raise SourceUnavailable(marketplace, f"{method} {url} failed after {self.retries + 1} attempts: {last_error}")

    async def get_json(self, marketplace: str, url: str, *, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None) -> Any:
        response = await self._request(marketplace, "GET", url, headers=headers, params=params)
        try:
            return response.json()
        except ValueError as exc:
            raise SourceUnavailable(marketplace, f"GET {url} returned invalid JSON") from exc

    async def get_text(self, marketplace: str, url: str, *, headers: dict[str, str] | None = None) -> str:
        return (await self._request(marketplace, "GET", url, headers=headers)).text
