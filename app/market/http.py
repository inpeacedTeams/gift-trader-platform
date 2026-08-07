import asyncio
from collections import defaultdict
from typing import Any
from urllib.parse import urlparse
import httpx
from .models import SourceUnavailable

class MarketHttp:
    def __init__(self, timeout: float = 20.0, retries: int = 2, backoff_seconds: float = 0.5, user_agent: str = "GiftTrader/0.1", max_concurrency_per_host: int = 4):
        self.timeout = timeout; self.retries = retries; self.backoff_seconds = backoff_seconds; self.user_agent = user_agent
        self._semaphores: dict[str, asyncio.Semaphore] = defaultdict(lambda: asyncio.Semaphore(max_concurrency_per_host))
    async def _request(self, marketplace: str, method: str, url: str, *, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None) -> httpx.Response:
        request_headers = {"User-Agent": self.user_agent, "Accept": "application/json", **(headers or {})}; host = urlparse(url).netloc; last_error: Exception | None = None
        async with self._semaphores[host]:
            for attempt in range(self.retries + 1):
                try:
                    async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client: response = await client.request(method, url, headers=request_headers, params=params)
                    if response.status_code in (429, 500, 502, 503, 504) and attempt < self.retries:
                        retry_after = response.headers.get("retry-after"); delay = float(retry_after) if retry_after and retry_after.replace(".", "", 1).isdigit() else self.backoff_seconds * (2 ** attempt); await asyncio.sleep(min(delay, 30)); continue
                    response.raise_for_status(); return response
                except httpx.HTTPError as exc:
                    last_error = exc
                    if attempt < self.retries: await asyncio.sleep(self.backoff_seconds * (2 ** attempt))
        raise SourceUnavailable(marketplace, f"{method} {url} failed after {self.retries + 1} attempts: {last_error}")
    async def get_json(self, marketplace: str, url: str, *, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None) -> Any:
        response = await self._request(marketplace, "GET", url, headers=headers, params=params)
        try: return response.json()
        except ValueError as exc: raise SourceUnavailable(marketplace, f"GET {url} returned invalid JSON") from exc
    async def get_text(self, marketplace: str, url: str, *, headers: dict[str, str] | None = None) -> str:
        return (await self._request(marketplace, "GET", url, headers=headers)).text
