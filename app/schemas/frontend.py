from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CollectionCard(BaseModel):
    id: int
    name: str
    slug: str | None = None
    chain_address: str | None = None
    gift_count: int = 0
    listings_count: int = 0
    floor_ton: Decimal | None = None
    image_url: str | None = None


class CollectionList(BaseModel):
    data_mode: str = "persisted"
    items: list[CollectionCard]


class GiftCard(BaseModel):
    id: int
    canonical_id: str
    collection_id: int | None = None
    collection_name: str | None = None
    name: str | None = None
    model: str | None = None
    gift_number: int | None = None
    image_url: str | None = None
    floor_ton: Decimal | None = None
    median_ton: Decimal | None = None
    listings_count: int = 0
    change_percent: Decimal | None = None


class GiftPage(BaseModel):
    data_mode: str = "persisted"
    items: list[GiftCard]
    page: int
    page_size: int
    total: int
    has_next: bool


class GiftListing(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    marketplace: str
    external_id: str
    price_ton: Decimal
    seller: str | None = None
    url: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    active: bool


class GiftDetail(GiftCard):
    listings: list[GiftListing]
    sources: list[str]


class PricePoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    observed_at: datetime
    marketplace: str
    floor_ton: Decimal | None
    median_ton: Decimal | None
    volume_ton: Decimal | None
    listings_count: int


class GiftHistory(BaseModel):
    data_mode: str = "persisted"
    gift_id: int
    points: list[PricePoint]
