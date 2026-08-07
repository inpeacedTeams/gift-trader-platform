from decimal import Decimal
from typing import Any
from app.core.config import get_settings
from app.market.http import MarketHttp

class TonapiPortfolioClient:
    def __init__(self, http: MarketHttp | None = None):
        settings = get_settings()
        self.base_url = settings.tonapi_base_url.rstrip("/")
        self.token = settings.tonapi_token
        self.http = http or MarketHttp(timeout=settings.source_timeout_seconds, retries=settings.source_retries, backoff_seconds=settings.source_backoff_seconds)
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}
    async def account(self, address: str) -> dict[str, Any]:
        return await self.http.get_json("tonapi", f"{self.base_url}/v2/accounts/{address}", headers=self._headers())
    async def nft_items(self, address: str) -> list[dict[str, Any]]:
        payload = await self.http.get_json("tonapi", f"{self.base_url}/v2/accounts/{address}/nfts", headers=self._headers(), params={"limit": 100})
        return payload.get("nft_items", []) if isinstance(payload, dict) else []
    @staticmethod
    def ton_balance(account: dict[str, Any]) -> Decimal:
        return Decimal(str(account.get("balance", 0))) / Decimal(1_000_000_000)
