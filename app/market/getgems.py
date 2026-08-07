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
            source = f"{self.tonapi_base}/v2/nfts/collections/{address}/items"
            payload = await self.http.get_json("getgems", source, params={"limit": 100})
            for item in payload.get("nft_items", []):
                sale = item.get("sale") or {}
                marketplace = str(sale.get("marketplace") or {}).lower()
                if marketplace and "getgems" not in marketplace:
                    continue
                price = sale.get("price", {}).get("value")
                nft_address = item.get("address")
                if not price or not nft_address:
                    continue
                metadata = item.get("metadata") or {}
                listings.append(Listing(
                    marketplace="getgems", listing_id=str(nft_address), gift_id=str(nft_address),
                    canonical_id=str(nft_address), collection_id=address,
                    collection_name=metadata.get("collection_name"), name=metadata.get("name"),
                    price_ton=Decimal(str(price)) / Decimal(1_000_000_000),
                    url=HttpUrl(f"https://getgems.io/nft/{nft_address}"), observed_at=now,
                    source_url=HttpUrl(source),
                ))
        return MarketSnapshot(marketplace="getgems", observed_at=now, listings=listings, source_url=HttpUrl("https://getgems.io"))
