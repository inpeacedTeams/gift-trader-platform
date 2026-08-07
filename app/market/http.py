from typing import Any
import httpx

from .models import SourceUnavailable


class MarketHttp:
    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    async def get_json(self, marketplace: str, url: str, *, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None) -> Any:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SourceUnavailable(marketplace, f"GET {url} failed: {exc}") from exc

    async def get_text(self, marketplace: str, url: str, *, headers: dict[str, str] | None = None) -> str:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.text
        except httpx.HTTPError as exc:
            raise SourceUnavailable(marketplace, f"GET {url} failed: {exc}") from exc
