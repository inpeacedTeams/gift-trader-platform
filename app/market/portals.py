from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import HttpUrl

from .base import MarketParser
from .http import MarketHttp
from .models import Listing, MarketSnapshot, SourceUnavailable

DEFAULT_ENDPOINT = "https://portals-market.com/api/nfts/search"
PAGE_LIMIT = 100


class PortalsParser(MarketParser):
    marketplace = "portals"

    def __init__(
        self,
        http: MarketHttp,
        endpoint: str = DEFAULT_ENDPOINT,
        auth_data: str | None = None,
    ):
        self.http = http
        self.endpoint = (endpoint or DEFAULT_ENDPOINT).rstrip("/")
        self.auth_data = auth_data

    @property
    def _headers(self) -> dict[str, str]:
        auth = self.auth_data or ""
        if auth and not auth.lower().startswith("tma "):
            auth = f"tma {auth}"
        return {"Authorization": auth}

    @staticmethod
    def _rows(payload: Any) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []
        for key in ("results", "gifts", "items", "nfts"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return rows
        return []

    @staticmethod
    def _model(row: dict[str, Any]) -> str | None:
        model = row.get("model")
        if model:
            return str(model)
        for attribute in row.get("attributes") or []:
            if isinstance(attribute, dict) and attribute.get("type") == "model":
                return str(attribute.get("value"))
        return None

    async def snapshot(self) -> MarketSnapshot:
        if not self.auth_data:
            raise SourceUnavailable(
                "portals",
                "no auth data configured: set PORTALS_AUTH_DATA with Telegram mini app initData",
            )
        now = datetime.now(timezone.utc)
        payload = await self.http.get_json(
            "portals",
            self.endpoint,
            headers=self._headers,
            params={
                "offset": 0,
                "limit": PAGE_LIMIT,
                "sort_by": "price asc",
                "status": "listed",
            },
        )
        listings: list[Listing] = []
        for row in self._rows(payload):
            if not isinstance(row, dict):
                continue
            raw_price = row.get("price") or row.get("price_ton") or row.get("amount")
            if raw_price is None:
                continue
            try:
                price = Decimal(str(raw_price))
            except Exception:
                continue
            canonical = (
                row.get("address")
                or row.get("nft_address")
                or row.get("nft_item_address")
            )
            listing_id = str(row.get("id") or row.get("tg_id") or canonical or "")
            if not listing_id or price <= 0:
                continue
            item_url = row.get("url") or row.get("link")
            listings.append(
                Listing(
                    marketplace="portals",
                    listing_id=listing_id,
                    gift_id=str(row.get("tg_id") or listing_id),
                    canonical_id=str(canonical) if canonical else None,
                    collection_id=str(row.get("collection_id"))
                    if row.get("collection_id")
                    else None,
                    collection_name=row.get("collection_name"),
                    name=row.get("name"),
                    model=self._model(row),
                    price_ton=price,
                    url=HttpUrl(item_url) if item_url else None,
                    seller=str(row.get("owner_id")) if row.get("owner_id") else None,
                    observed_at=now,
                    source_url=HttpUrl(self.endpoint),
                )
            )
        return MarketSnapshot(
            marketplace="portals",
            observed_at=now,
            listings=listings,
            source_url=HttpUrl(self.endpoint),
        )
