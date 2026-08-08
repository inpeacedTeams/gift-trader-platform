from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CollectionCard(BaseModel):
    id: int
    name: str | None = None
    slug: str | None = None
    chain_address: str
    gift_count: int = 0
    listings_count: int = 0
    floor_ton: Decimal | None = None
    image_url: str | None = None


class CollectionPage(BaseModel):
    data_mode: str = "persisted"
    items: list[CollectionCard]
    page: int
    page_size: int
    total: int
    has_next: bool


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
    best_marketplace: str | None = None
    deal_percent: Decimal | None = None


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


class MarketEventCard(BaseModel):
    """One change on the market: a new listing, a reprice or a delisting."""

    id: int
    gift_id: int
    name: str | None = None
    model: str | None = None
    image_url: str | None = None
    collection_name: str | None = None
    marketplace: str
    event_type: str
    price_ton: Decimal | None = None
    previous_ton: Decimal | None = None
    change_percent: Decimal | None = None
    occurred_at: datetime


class MarketEventFeed(BaseModel):
    data_mode: str = "persisted"
    items: list[MarketEventCard]
    latest_id: int | None = None


class TradeRecord(BaseModel):
    """A sale that actually happened."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    marketplace: str
    price_ton: Decimal
    seller: str | None = None
    buyer: str | None = None
    traded_at: datetime


class TradeStats(BaseModel):
    window_days: int
    sales_count: int = 0
    lowest_ton: Decimal | None = None
    highest_ton: Decimal | None = None
    median_ton: Decimal | None = None
    volume_ton: Decimal | None = None
    last_sold_at: datetime | None = None


class GiftTrades(BaseModel):
    data_mode: str = "persisted"
    gift_id: int
    stats: TradeStats
    items: list[TradeRecord]


class Deal(BaseModel):
    """An active listing priced below the median of its own model."""

    gift_id: int
    name: str | None = None
    model: str | None = None
    gift_number: int | None = None
    image_url: str | None = None
    collection_id: int | None = None
    collection_name: str | None = None
    marketplace: str
    price_ton: Decimal
    median_ton: Decimal
    peer_count: int
    discount_percent: Decimal
    url: str | None = None


class DealList(BaseModel):
    data_mode: str = "persisted"
    items: list[Deal]


class MoverCard(BaseModel):
    """A gift whose floor moved inside the requested window."""

    gift_id: int
    name: str | None = None
    model: str | None = None
    image_url: str | None = None
    collection_id: int | None = None
    collection_name: str | None = None
    floor_ton: Decimal
    previous_ton: Decimal
    change_percent: Decimal


class MoversResponse(BaseModel):
    data_mode: str = "persisted"
    window_hours: int
    gainers: list[MoverCard]
    losers: list[MoverCard]
