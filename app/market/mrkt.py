from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import HttpUrl

from .base import MarketParser
from .http import MarketHttp
from .models import Listing, MarketSnapshot, SourceUnavailable
from .tonnel import gift_slug, strip_rarity

DEFAULT_BASE = "https://api.tgmrkt.io/api/v1"
NANOTON = Decimal(1_000_000_000)
# The API caps a page at 20 regardless of what we ask for.
PAGE_SIZE = 20
HARD_PAGE_CAP = 300


class MrktParser(MarketParser):
    """Listings from MRKT.

    Reads with a bearer token that the marketplace mints from Telegram mini
    app init data. Pagination is cursor based, not offset based, so a shifting
    book never makes us skip or repeat a page.
    """

    marketplace = "mrkt"

    def __init__(
        self,
        http: MarketHttp,
        base_url: str = DEFAULT_BASE,
        token: str | None = None,
        init_data: str | None = None,
        max_pages: int = HARD_PAGE_CAP,
    ):
        self.http = http
        self.base_url = (base_url or DEFAULT_BASE).rstrip("/")
        self.token = token
        self.init_data = init_data
        self.max_pages = max(1, min(max_pages, HARD_PAGE_CAP))

    async def _ensure_token(self) -> str:
        """Trade init data for a bearer token, once per crawl."""
        if self.token:
            return self.token
        if not self.init_data:
            raise SourceUnavailable(
                "mrkt",
                "no credentials: set MRKT_TOKEN or MRKT_INIT_DATA",
            )
        payload = await self.http.post_json(
            "mrkt", f"{self.base_url}/auth", json_body={"data": self.init_data}
        )
        token = payload.get("token") if isinstance(payload, dict) else None
        if not token:
            raise SourceUnavailable("mrkt", "auth returned no token, init data is stale")
        self.token = str(token)
        return self.token

    def _headers(self, token: str) -> dict[str, str]:
        return {"Authorization": token, "Referer": "https://cdn.tgmrkt.io/"}

    @staticmethod
    def _payload(cursor: str) -> dict[str, Any]:
        return {
            "collectionNames": [],
            "modelNames": [],
            "backdropNames": [],
            "symbolNames": [],
            "ordering": "Price",
            "lowToHigh": True,
            "maxPrice": None,
            "minPrice": None,
            "mintable": None,
            "number": None,
            "count": PAGE_SIZE,
            "cursor": cursor,
            "query": None,
            "promotedFirst": False,
        }

    @staticmethod
    def _price_ton(row: dict[str, Any]) -> Decimal | None:
        raw = row.get("price") or row.get("salePrice") or row.get("amount")
        if raw is None:
            return None
        try:
            value = Decimal(str(raw))
        except Exception:
            return None
        # Prices come in nanoton. A plain float would already be a red flag,
        # but the magnitude check keeps a format change from inventing prices.
        if value > 10_000_000:
            value = value / NANOTON
        return value if value > 0 else None

    @staticmethod
    def _attribute(row: dict[str, Any], key: str) -> str | None:
        value = row.get(key) or row.get(f"{key}Name")
        return strip_rarity(value) if value else None

    def _listing(self, row: dict[str, Any], now: datetime) -> Listing | None:
        price = self._price_ton(row)
        if price is None:
            return None
        listing_id = str(row.get("id") or row.get("giftId") or "")
        if not listing_id:
            return None
        name = row.get("collectionName") or row.get("name") or row.get("title")
        number = row.get("number") or row.get("externalCollectionNumber")
        try:
            gift_number = int(number) if number is not None else None
        except (TypeError, ValueError):
            gift_number = None
        slug = gift_slug(name)
        image = row.get("photoUrl") or row.get("imageUrl")
        if not image and slug and gift_number is not None:
            image = f"https://nft.fragment.com/gift/{slug.lower()}-{gift_number}.medium.jpg"
        url = (
            f"https://t.me/nft/{slug}-{gift_number}"
            if slug and gift_number is not None
            else "https://t.me/mrkt"
        )
        return Listing(
            marketplace="mrkt",
            listing_id=listing_id,
            gift_id=listing_id,
            canonical_id=str(row["address"]) if row.get("address") else None,
            collection_name=name,
            gift_number=gift_number,
            name=name,
            model=self._attribute(row, "model"),
            image_url=HttpUrl(str(image)) if image else None,
            price_ton=price,
            url=HttpUrl(url),
            seller=str(row["ownerId"]) if row.get("ownerId") else None,
            observed_at=now,
            source_url=HttpUrl(f"{self.base_url}/gifts/saling"),
        )

    async def snapshot(self) -> MarketSnapshot:
        token = await self._ensure_token()
        now = datetime.now(timezone.utc)
        source = f"{self.base_url}/gifts/saling"
        listings: list[Listing] = []
        seen: set[str] = set()
        cursor = ""
        for _ in range(self.max_pages):
            payload = await self.http.post_json(
                "mrkt", source, headers=self._headers(token), json_body=self._payload(cursor)
            )
            if not isinstance(payload, dict):
                break
            rows = payload.get("gifts") or []
            if not rows:
                break
            for row in rows:
                if not isinstance(row, dict):
                    continue
                listing = self._listing(row, now)
                if listing is None or listing.listing_id in seen:
                    continue
                seen.add(listing.listing_id)
                listings.append(listing)
            cursor = payload.get("cursor") or ""
            # An empty cursor is the marketplace saying there is nothing after this.
            if not cursor or len(rows) < PAGE_SIZE:
                break
        return MarketSnapshot(
            marketplace="mrkt",
            observed_at=now,
            listings=listings,
            source_url=HttpUrl(source),
        )
