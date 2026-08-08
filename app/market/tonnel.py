import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import HttpUrl

from .base import MarketParser
from .http import MarketHttp
from .models import Listing, MarketSnapshot
from .rarity import split_rarity, strip_rarity

DEFAULT_ENDPOINT = "https://gifts2.tonnel.network/api/pageGifts"
# 30 is the hard server side maximum, larger values return an error.
PAGE_LIMIT = 30
# Safety stop. Reaching it means the cursor is broken, not that the market is huge.
HARD_PAGE_CAP = 400
BASE_FILTER = {
    "price": {"$exists": True},
    "refunded": {"$ne": True},
    "buyer": {"$exists": False},
    "export_at": {"$exists": True},
    "asset": "TON",
}
# Cheapest first is a stable order: new listings appear at a predictable place
# instead of shifting every row like a recency sort does.
SORT_BY_PRICE = {"price": 1, "gift_id": -1}

__all__ = [
    "DEFAULT_ENDPOINT",
    "HARD_PAGE_CAP",
    "PAGE_LIMIT",
    "TonnelParser",
    "gift_slug",
    "split_rarity",
    "strip_rarity",
]


def gift_slug(gift_name: str | None) -> str | None:
    """'Plush Pepe' -> 'PlushPepe', the slug used by Telegram gift URLs."""
    if not gift_name:
        return None
    return re.sub(r"[^A-Za-z0-9]", "", gift_name) or None


class TonnelParser(MarketParser):
    """Public Tonnel listings. Browsing needs no credentials."""

    marketplace = "tonnel"

    def __init__(
        self,
        http: MarketHttp,
        endpoint: str = DEFAULT_ENDPOINT,
        max_pages: int = HARD_PAGE_CAP,
    ):
        self.http = http
        self.endpoint = endpoint or DEFAULT_ENDPOINT
        self.max_pages = max(1, min(max_pages, HARD_PAGE_CAP))

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Origin": "https://market.tonnel.network",
            "Referer": "https://market.tonnel.network/",
        }

    def _payload(self, page: int) -> dict[str, Any]:
        return {
            "page": page,
            "limit": PAGE_LIMIT,
            "sort": json.dumps(SORT_BY_PRICE),
            "filter": json.dumps(BASE_FILTER),
            "price_range": None,
            "user_auth": "",
        }

    @staticmethod
    def _rows(payload: Any) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("gifts", "results", "items", "data"):
                rows = payload.get(key)
                if isinstance(rows, list):
                    return rows
        return []

    @staticmethod
    def _url(slug: str | None, gift_number: int | None) -> HttpUrl:
        if slug and gift_number is not None:
            return HttpUrl(f"https://t.me/nft/{slug}-{gift_number}")
        return HttpUrl("https://market.tonnel.network/")

    @staticmethod
    def _image(row: dict[str, Any], slug: str | None, gift_number: int | None) -> HttpUrl | None:
        for key in ("photo_url", "image_url", "image"):
            value = row.get(key)
            if value:
                return HttpUrl(str(value))
        if slug and gift_number is not None:
            return HttpUrl(
                f"https://nft.fragment.com/gift/{slug.lower()}-{gift_number}.medium.jpg"
            )
        return None

    @staticmethod
    def _gift_number(row: dict[str, Any]) -> int | None:
        raw = row.get("gift_num") or row.get("gift_number") or row.get("number")
        try:
            number = int(raw)
        except (TypeError, ValueError):
            return None
        return number if number >= 0 else None

    def _listing(self, row: dict[str, Any], now: datetime) -> Listing | None:
        raw_price = row.get("price")
        if raw_price is None:
            return None
        try:
            price = Decimal(str(raw_price))
        except Exception:
            return None
        if price <= 0:
            return None
        listing_id = str(row.get("gift_id") or row.get("_id") or "")
        if not listing_id:
            return None
        gift_name = row.get("gift_name") or row.get("name")
        gift_number = self._gift_number(row)
        slug = gift_slug(gift_name)
        # Tonnel writes rarity into the attribute itself: "Albino (1.5%)".
        model, model_rarity = split_rarity(row.get("model"))
        backdrop, backdrop_rarity = split_rarity(row.get("backdrop"))
        symbol, symbol_rarity = split_rarity(row.get("symbol") or row.get("pattern"))
        return Listing(
            marketplace="tonnel",
            listing_id=listing_id,
            gift_id=listing_id,
            canonical_id=str(row["nft_address"]) if row.get("nft_address") else None,
            collection_name=gift_name,
            gift_number=gift_number,
            name=gift_name,
            model=model,
            model_rarity=model_rarity,
            backdrop=backdrop,
            backdrop_rarity=backdrop_rarity,
            symbol=symbol,
            symbol_rarity=symbol_rarity,
            image_url=self._image(row, slug, gift_number),
            price_ton=price,
            url=self._url(slug, gift_number),
            seller=str(row.get("owner")) if row.get("owner") else None,
            observed_at=now,
            source_url=HttpUrl(self.endpoint),
        )

    async def snapshot(self) -> MarketSnapshot:
        """Walk every page until the book runs out.

        Two stop conditions matter: a short page means the end, and a page
        that only repeats ids we already hold means the cursor is stuck,
        which happens when listings shift between requests.
        """
        now = datetime.now(timezone.utc)
        listings: list[Listing] = []
        seen: set[str] = set()
        for page in range(1, self.max_pages + 1):
            payload = await self.http.post_json(
                "tonnel", self.endpoint, headers=self._headers, json_body=self._payload(page)
            )
            rows = self._rows(payload)
            if not rows:
                break
            fresh = 0
            for row in rows:
                if not isinstance(row, dict):
                    continue
                listing = self._listing(row, now)
                if listing is None or listing.listing_id in seen:
                    continue
                seen.add(listing.listing_id)
                listings.append(listing)
                fresh += 1
            if fresh == 0 or len(rows) < PAGE_LIMIT:
                break
        return MarketSnapshot(
            marketplace="tonnel",
            observed_at=now,
            listings=listings,
            source_url=HttpUrl(self.endpoint),
        )
