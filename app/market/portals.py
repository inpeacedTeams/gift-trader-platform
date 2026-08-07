from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from pydantic import HttpUrl
from .base import MarketParser
from .http import MarketHttp
from .models import Listing, MarketSnapshot

class PortalsParser(MarketParser):
    marketplace = "portals"
    def __init__(self, http: MarketHttp, endpoint: str = "https://portal-market.com/api"):
        self.http = http
        self.endpoint = endpoint.rstrip("/")

    async def snapshot(self) -> MarketSnapshot:
        now = datetime.now(timezone.utc)
        payload = await self.http.get_json("portals", self.endpoint, params={"limit": 100, "sort": "price_asc"})
        rows: list[Any] = payload if isinstance(payload, list) else payload.get("gifts", payload.get("items", payload.get("results", [])))
        listings: list[Listing] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            raw_price = row.get("price") or row.get("price_ton") or row.get("amount")
            if raw_price is None:
                continue
            try:
                price = Decimal(str(raw_price))
            except Exception:
                continue
            listing_id = str(row.get("id") or row.get("tg_id") or row.get("address") or "")
            if not listing_id or price <= 0:
                continue
            item_url = row.get("url") or row.get("link")
            listings.append(Listing(
                marketplace="portals", listing_id=listing_id, gift_id=str(row.get("tg_id") or listing_id),
                collection_id=str(row.get("collection_id")) if row.get("collection_id") else None,
                name=row.get("name"), price_ton=price,
                url=HttpUrl(item_url) if item_url else None,
                seller=str(row.get("owner_id")) if row.get("owner_id") else None,
                observed_at=now, source_url=HttpUrl(self.endpoint),
            ))
        return MarketSnapshot(marketplace="portals", observed_at=now, listings=listings, source_url=HttpUrl(self.endpoint))
