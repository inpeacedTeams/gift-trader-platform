from collections.abc import AsyncIterator
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import HttpUrl

from .base import MarketParser
from .http import MarketHttp
from .models import Listing, MarketSnapshot, SourceUnavailable

NANOTON = Decimal(1_000_000_000)
PAGE_LIMIT = 100
MAX_PAGES = 20


class GetGemsParser(MarketParser):
    marketplace = "getgems"

    def __init__(
        self,
        http: MarketHttp,
        collection_addresses: list[str],
        tonapi_base: str = "https://tonapi.io",
        api_token: str | None = None,
    ):
        self.http = http
        self.collection_addresses = collection_addresses
        self.tonapi_base = tonapi_base.rstrip("/")
        self.api_token = api_token

    @property
    def _headers(self) -> dict[str, str]:
        if not self.api_token:
            return {}
        return {"Authorization": f"Bearer {self.api_token}"}

    @staticmethod
    def _market_name(sale: dict[str, Any]) -> str:
        market = sale.get("market") or sale.get("marketplace") or {}
        if isinstance(market, dict):
            return str(market.get("name") or market.get("address") or "").lower()
        return str(market).lower()

    @staticmethod
    def _price_ton(sale: dict[str, Any]) -> Decimal | None:
        price = sale.get("price")
        raw = price.get("value") if isinstance(price, dict) else price
        if raw is None:
            return None
        try:
            value = Decimal(str(raw)) / NANOTON
        except Exception:
            return None
        return value if value > 0 else None

    async def _items(self, address: str) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        source = f"{self.tonapi_base}/v2/nfts/collections/{address}/items"
        for page in range(MAX_PAGES):
            payload = await self.http.get_json(
                "getgems",
                source,
                headers=self._headers,
                params={"limit": PAGE_LIMIT, "offset": page * PAGE_LIMIT},
            )
            items = payload.get("nft_items") or [] if isinstance(payload, dict) else []
            for item in items:
                if isinstance(item, dict):
                    yield source, item
            if len(items) < PAGE_LIMIT:
                return

    async def snapshot(self) -> MarketSnapshot:
        if not self.collection_addresses:
            raise SourceUnavailable(
                "getgems",
                "no collection addresses configured: set GETGEMS_COLLECTION_ADDRESSES",
            )
        now = datetime.now(timezone.utc)
        listings: list[Listing] = []
        for address in self.collection_addresses:
            async for source, item in self._items(address):
                sale = item.get("sale") or {}
                if not isinstance(sale, dict) or not sale:
                    continue
                market = self._market_name(sale)
                if market and "getgems" not in market:
                    continue
                price_ton = self._price_ton(sale)
                nft_address = item.get("address")
                if price_ton is None or not nft_address:
                    continue
                metadata = item.get("metadata") or {}
                collection = item.get("collection") or {}
                owner = sale.get("owner") or {}
                listings.append(
                    Listing(
                        marketplace="getgems",
                        listing_id=str(sale.get("address") or nft_address),
                        gift_id=str(nft_address),
                        canonical_id=str(nft_address),
                        collection_id=str(collection.get("address") or address),
                        collection_name=collection.get("name")
                        or metadata.get("collection_name"),
                        name=metadata.get("name"),
                        model=metadata.get("model"),
                        price_ton=price_ton,
                        url=HttpUrl(f"https://getgems.io/nft/{nft_address}"),
                        seller=str(owner.get("address")) if owner.get("address") else None,
                        observed_at=now,
                        source_url=HttpUrl(source),
                    )
                )
        return MarketSnapshot(
            marketplace="getgems",
            observed_at=now,
            listings=listings,
            source_url=HttpUrl("https://getgems.io"),
        )
