from datetime import datetime, timezone
from decimal import Decimal
from pydantic import HttpUrl

from .base import MarketParser
from .http import MarketHttp
from .models import Listing, MarketSnapshot

class GetGemsParser(MarketParser):
    marketplace = "getgems"

    def __init__(self, http: MarketHttp, collection_addresses: list[str], tonapi_base: str = "https://tonapi.io"):
        self.http = http
        self.collection_addresses = collection_addresses
        self.tonapi_base = tonapi_base.rstrip("/")

    async def snapshot(self) -> MarketSnapshot:
        now = datetime.now(timezone.utc)
        listings: list[Listing] = []
        for address in self.collection_addresses:
            payload = await self.http.get_json("getgems", f"{self.tonapi_base}/v2/nfts/collections/{address}/items", params={"limit": 100})
            for item in payload.get("nft_items", []):
                sale = item.get("sale") or {}
                if sale.get("marketplace", {}).get("address") and "getgems" not in str(sale.get("marketplace")) .lower():
                    continue
                price = sale.get("price", {}).get("value")
                if not price:
                    continue
                listings.append(Listing(
                    marketplace="getgems", listing_id=str(item.get("address")), gift_id=str(item.get("address")),
                    collection_id=address, name=item.get("metadata", {}).get("name"),
                    price_ton=Decimal(str(price)) / Decimal(1_000_000_000),
                    url=HttpUrl(f"https://getgems.io/nft/{item.get('address')}"), observed_at=now,
                    source_url=HttpUrl(f"{self.tonapi_base}/v2/nfts/collections/{address}/items"),
                ))
        return MarketSnapshot(marketplace="getgems", observed_at=now, listings=listings, source_url=HttpUrl("https://getgems.io"))
