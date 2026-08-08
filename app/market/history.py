import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, HttpUrl

from .http import MarketHttp
from .models import SourceUnavailable
from .tonnel import gift_slug, strip_rarity

DEFAULT_ENDPOINT = "https://gifts2.tonnel.network/api/saleHistory"
PAGE_LIMIT = 50
MAX_PAGES = 20
SORT_BY_LATEST = {"timestamp": -1, "gift_id": -1}


class Trade(BaseModel):
    """A completed sale. Unlike a listing, this price was actually paid."""

    marketplace: str
    external_id: str
    canonical_id: str | None = None
    collection_name: str | None = None
    gift_number: int | None = Field(default=None, ge=0)
    name: str | None = None
    model: str | None = None
    price_ton: Decimal = Field(gt=0)
    seller: str | None = None
    buyer: str | None = None
    traded_at: datetime
    source_url: HttpUrl


def parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Tonnel sends seconds, some rows arrive in milliseconds.
        seconds = value / 1000 if value > 1e11 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class TonnelSaleHistory:
    """Completed sales from Tonnel.

    Listings only show what sellers hope to get. Trades are the number the
    market actually agreed on, so valuation leans on these first.
    """

    marketplace = "tonnel"

    def __init__(self, http: MarketHttp, endpoint: str = DEFAULT_ENDPOINT, auth_data: str | None = None):
        self.http = http
        self.endpoint = endpoint or DEFAULT_ENDPOINT
        self.auth_data = auth_data

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Origin": "https://market.tonnel.network",
            "Referer": "https://market.tonnel.network/",
        }

    def _payload(self, page: int) -> dict[str, Any]:
        return {
            "authData": self.auth_data or "",
            "page": page,
            "limit": PAGE_LIMIT,
            "type": "SALE",
            "filter": {},
            "sort": SORT_BY_LATEST,
        }

    @staticmethod
    def _rows(payload: Any) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("results", "gifts", "items", "data", "history"):
                rows = payload.get(key)
                if isinstance(rows, list):
                    return rows
        return []

    @staticmethod
    def _gift_number(row: dict[str, Any]) -> int | None:
        raw = row.get("gift_num") or row.get("gift_number")
        try:
            number = int(raw)
        except (TypeError, ValueError):
            return None
        return number if number >= 0 else None

    def _trade(self, row: dict[str, Any]) -> Trade | None:
        if str(row.get("asset") or "TON").upper() != "TON":
            return None
        raw_price = row.get("price") or row.get("amount")
        if raw_price is None:
            return None
        try:
            price = Decimal(str(raw_price))
        except Exception:
            return None
        if price <= 0:
            return None
        traded_at = parse_timestamp(row.get("timestamp") or row.get("time") or row.get("sold_at"))
        if traded_at is None:
            return None
        external_id = str(row.get("_id") or row.get("sale_id") or row.get("gift_id") or "")
        if not external_id:
            return None
        gift_name = row.get("gift_name") or row.get("name")
        return Trade(
            marketplace="tonnel",
            external_id=external_id,
            canonical_id=str(row["nft_address"]) if row.get("nft_address") else None,
            collection_name=gift_name,
            gift_number=self._gift_number(row),
            name=gift_name,
            model=strip_rarity(row.get("model")),
            price_ton=price,
            seller=str(row["seller"]) if row.get("seller") else None,
            buyer=str(row["buyer"]) if row.get("buyer") else None,
            traded_at=traded_at,
            source_url=HttpUrl(self.endpoint),
        )

    async def fetch(self, max_pages: int = MAX_PAGES) -> list[Trade]:
        if not self.auth_data:
            raise SourceUnavailable(
                "tonnel-history",
                "no auth data configured: set TONNEL_AUTH_DATA to collect real sales",
            )
        trades: list[Trade] = []
        for page in range(1, max_pages + 1):
            payload = await self.http.post_json(
                "tonnel-history",
                self.endpoint,
                headers=self._headers,
                json_body=self._payload(page),
            )
            rows = self._rows(payload)
            for row in rows:
                if not isinstance(row, dict):
                    continue
                trade = self._trade(row)
                if trade is not None:
                    trades.append(trade)
            if len(rows) < PAGE_LIMIT:
                break
        return trades


def trade_identity(trade: Trade) -> str:
    """Same key scheme the listings use, so a sale lands on the right gift."""
    from .identity import normalize_address, normalize_text
    from hashlib import sha256

    if trade.canonical_id:
        return f"canonical:{normalize_address(trade.canonical_id)}"
    collection = normalize_text(trade.collection_name)
    name = normalize_text(trade.name)
    if collection and name and trade.model:
        name = f"{name} {normalize_text(trade.model)}"
    if collection and name:
        raw = f"derived:{collection}:{name}"
        return "derived:" + sha256(raw.encode()).hexdigest()[:24]
    return f"unresolved:tonnel:{normalize_address(trade.external_id)}"


def slug_for(trade: Trade) -> str | None:
    return gift_slug(trade.name)


def dumps_filter(value: dict[str, Any]) -> str:
    return json.dumps(value)
