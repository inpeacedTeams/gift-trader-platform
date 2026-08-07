from datetime import datetime, timezone
from decimal import Decimal
from app.market.core import MarketplaceCosts, find_arbitrage
from app.market.models import Listing, MarketSnapshot


def listing(marketplace: str, price: str, canonical_id: str = "EQgift") -> Listing:
    now = datetime.now(timezone.utc)
    return Listing(marketplace=marketplace, listing_id=f"{marketplace}-1", gift_id="gift-1", canonical_id=canonical_id, price_ton=Decimal(price), observed_at=now, source_url="https://example.com")


def snapshots(buy_price: str, sell_price: str, canonical_id: str = "EQgift") -> list[MarketSnapshot]:
    buy = listing("portals", buy_price, canonical_id)
    sell = listing("getgems", sell_price, canonical_id)
    return [MarketSnapshot(marketplace="portals", observed_at=buy.observed_at, listings=[buy], source_url="https://example.com"), MarketSnapshot(marketplace="getgems", observed_at=sell.observed_at, listings=[sell], source_url="https://example.com")]


def test_arbitrage_is_net_of_fees():
    result = find_arbitrage(snapshots("10", "12"), {"getgems": MarketplaceCosts(fee_percent=Decimal("2"))})
    assert len(result) == 1
    assert result[0].profit_ton == Decimal("1.76")


def test_no_opportunity_when_fee_erases_spread():
    assert find_arbitrage(snapshots("10", "10.1"), {"getgems": MarketplaceCosts(fee_percent=Decimal("2"))}) == []


def test_unresolved_identity_is_not_used_for_arbitrage():
    assert find_arbitrage(snapshots("10", "12", canonical_id=None), {}) == []
