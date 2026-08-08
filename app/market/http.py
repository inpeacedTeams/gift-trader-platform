import asyncio
from collections import defaultdict
from typing import Any
from urllib.parse import urlparse

import httpx

from .models import SourceUnavailable

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)
RETRYABLE_STATUS = (403, 429, 500, 502, 503, 504)


class MarketHttp:
    def __init__(
        self,
        timeout: float = 20.0,
        retries: int = 2,
        backoff_seconds: float = 0.5,
        user_agent: str = BROWSER_USER_AGENT,
        max_concurrency_per_host: int = 4,
    ):
        self.timeout = timeout
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.user_agent = user_agent
        self._semaphores: dict[str, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(max_concurrency_per_host)
        )

    def _default_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def _request(
        self,
        marketplace: str,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
    ) -> httpx.Response:
        request_headers = {**self._default_headers(), **(headers or {})}
        host = urlparse(url).netloc
        last_error: Exception | None = None
        async with self._semaphores[host]:
            for attempt in range(self.retries + 1):
                try:
                    async with httpx.AsyncClient(
                        timeout=self.timeout, follow_redirects=True
                    ) as client:
                        response = await client.request(
                            method,
                            url,
                            headers=request_headers,
                            params=params,
                            json=json_body,
                        )
                    if response.status_code in RETRYABLE_STATUS and attempt < self.retries:
                        retry_after = response.headers.get("retry-after")
                        delay = (
                            float(retry_after)
                            if retry_after and retry_after.replace(".", "", 1).isdigit()
                            else self.backoff_seconds * (2**attempt)
                        )
                        await asyncio.sleep(min(delay, 30))
                        continue
                    response.raise_for_status()
                    return response
                except httpx.HTTPError as exc:
                    last_error = exc
                    if attempt < self.retries:
                        await asyncio.sleep(self.backoff_seconds * (2**attempt))
        raise SourceUnavailable(
            marketplace,
            f"{method} {url} failed after {self.retries + 1} attempts: {last_error}",
        )

    async def get_json(
        self,
        marketplace: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        response = await self._request(
            marketplace, "GET", url, headers=headers, params=params
        )
        return self._json(marketplace, url, response)

    async def post_json(
        self,
        marketplace: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
    ) -> Any:
        response = await self._request(
            marketplace, "POST", url, headers=headers, params=params, json_body=json_body
        )
        return self._json(marketplace, url, response)

    async def get_text(
        self, marketplace: str, url: str, *, headers: dict[str, str] | None = None
    ) -> str:
        return (await self._request(marketplace, "GET", url, headers=headers)).text

    @staticmethod
    def _json(marketplace: str, url: str, response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise SourceUnavailable(
                marketplace, f"{url} returned invalid JSON"
            ) from exc
