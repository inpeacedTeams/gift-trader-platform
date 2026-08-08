from decimal import Decimal

from pydantic import BaseModel


class MarketplaceFee(BaseModel):
    """What a venue keeps when a gift sells there."""

    marketplace: str
    sell_fee_percent: Decimal


class FeeSchedule(BaseModel):
    """Every cost that stands between a buy price and money in hand.

    Published so the browser never hardcodes its own numbers: a profit figure
    computed with stale fees is worse than no profit figure at all.
    """

    data_mode: str = "static"
    gas_ton: Decimal
    default_sell_fee_percent: Decimal
    marketplaces: list[MarketplaceFee]
