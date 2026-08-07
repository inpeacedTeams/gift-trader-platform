from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl

Marketplace = Literal["fragment", "portals", "getgems", "tonapi"]

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
