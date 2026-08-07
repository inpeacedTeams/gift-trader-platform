from collections import defaultdict
from decimal import Decimal
from pydantic import BaseModel
from .models import Listing, MarketSnapshot

class MarketMetrics(BaseModel):
    marketplace: str
    listings_count: int
    gifts_count: int
    floor_ton: Decimal | None
    median_ton: Decimal | None
    volume_ton: Decimal
    liquidity_score: Decimal
    data_confidence: Decimal

class MarketOverview(BaseModel):
    markets: list[MarketMetrics]
    total_listings: int
    total_gifts: int
    total_volume_ton: Decimal
    best_floor_ton: Decimal | None

def _median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    values = sorted(values)
    return values[len(values) // 2]

def analyze_snapshot(snapshot: MarketSnapshot) -> MarketMetrics:
    by_gift: dict[str, list[Listing]] = defaultdict(list)
    for item in snapshot.listings:
        by_gift[item.canonical_id or item.gift_id].append(item)
    prices = [item.price_ton for item in snapshot.listings]
    volume = sum(prices, Decimal("0"))
    count = len(snapshot.listings)
    gifts = len(by_gift)
    verified = sum(1 for item in snapshot.listings if item.canonical_id)
    confidence = Decimal(verified) / Decimal(count) * Decimal("100") if count else Decimal("0")
    liquidity = min(Decimal("100"), Decimal(count) * Decimal("2"))
    return MarketMetrics(marketplace=snapshot.marketplace, listings_count=count, gifts_count=gifts, floor_ton=min(prices) if prices else None, median_ton=_median(prices), volume_ton=volume, liquidity_score=liquidity, data_confidence=confidence)

def overview(snapshots: list[MarketSnapshot]) -> MarketOverview:
    metrics = [analyze_snapshot(snapshot) for snapshot in snapshots]
    floors = [item.floor_ton for item in metrics if item.floor_ton is not None]
    return MarketOverview(markets=metrics, total_listings=sum(item.listings_count for item in metrics), total_gifts=sum(item.gifts_count for item in metrics), total_volume_ton=sum((item.volume_ton for item in metrics), Decimal("0")), best_floor_ton=min(floors) if floors else None)
