from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

Marketplace = Literal["fragment", "portals", "getgems", "tonnel", "mrkt", "tonapi"]

# A rarity share is a percentage of the collection: 0 is impossible, 100 means
# every gift has it. Anything else is a parsing accident and gets rejected.
RarityPercent = Field(default=None, gt=0, le=100)


class Listing(BaseModel):
    marketplace: Marketplace
    listing_id: str
    gift_id: str
    canonical_id: str | None = None
    collection_id: str | None = None
    collection_name: str | None = None
    gift_number: int | None = Field(default=None, ge=0)
    name: str | None = None
    model: str | None = None
    model_rarity: Decimal | None = RarityPercent
    backdrop: str | None = None
    backdrop_rarity: Decimal | None = RarityPercent
    symbol: str | None = None
    symbol_rarity: Decimal | None = RarityPercent
    image_url: HttpUrl | None = None
    price_ton: Decimal = Field(gt=0)
    url: HttpUrl | None = None
    seller: str | None = None
    listed_at: datetime | None = None
    observed_at: datetime
    source_url: HttpUrl


class MarketSnapshot(BaseModel):
    marketplace: Marketplace
    observed_at: datetime
    listings: list[Listing]
    source_url: HttpUrl


class SourceUnavailable(Exception):
    def __init__(self, marketplace: str, reason: str):
        self.marketplace = marketplace
        self.reason = reason
        super().__init__(f"{marketplace}: {reason}")
