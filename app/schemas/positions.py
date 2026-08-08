from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PositionCreate(BaseModel):
    gift_id: int
    buy_price_ton: Decimal = Field(gt=0)
    marketplace: str | None = Field(default=None, max_length=64)
    quantity: int = Field(default=1, ge=1, le=1000)
    opened_at: datetime | None = None
    note: str | None = Field(default=None, max_length=500)


class PositionUpdate(BaseModel):
    """Partial edit. Only the fields actually sent are applied.

    Sending sell_price_ton as null reopens the position, which is the honest
    way to undo a mistyped exit.
    """

    buy_price_ton: Decimal | None = Field(default=None, gt=0)
    quantity: int | None = Field(default=None, ge=1, le=1000)
    marketplace: str | None = Field(default=None, max_length=64)
    sell_price_ton: Decimal | None = Field(default=None, gt=0)
    sell_marketplace: str | None = Field(default=None, max_length=64)
    closed_at: datetime | None = None
    note: str | None = Field(default=None, max_length=500)


class PositionCard(BaseModel):
    id: int
    gift_id: int
    name: str | None = None
    model: str | None = None
    image_url: str | None = None
    rarity_tier: str | None = None
    gift_number: int | None = None
    collection_name: str | None = None
    marketplace: str | None = None
    buy_price_ton: Decimal
    quantity: int
    opened_at: datetime
    closed_at: datetime | None = None
    sell_price_ton: Decimal | None = None
    sell_marketplace: str | None = None
    note: str | None = None
    # Live market side. None means the gift has no active listing right now,
    # which is unknown value, not zero value.
    floor_ton: Decimal | None = None
    median_ton: Decimal | None = None
    exit_venue: str | None = None
    exit_net_ton: Decimal | None = None
    cost_basis_ton: Decimal
    profit_ton: Decimal | None = None
    roi_percent: Decimal | None = None
    is_open: bool


class PositionSummary(BaseModel):
    open_count: int = 0
    closed_count: int = 0
    # Open positions whose gift is not listed anywhere, so they carry no
    # current value and are excluded from the totals above.
    unpriced_count: int = 0
    invested_ton: Decimal = Decimal(0)
    market_value_ton: Decimal = Decimal(0)
    unrealized_ton: Decimal = Decimal(0)
    realized_ton: Decimal = Decimal(0)
    wins: int = 0
    win_rate_percent: Decimal | None = None


class PositionList(BaseModel):
    data_mode: str = "persisted"
    items: list[PositionCard]
    summary: PositionSummary
