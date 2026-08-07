from datetime import datetime, timezone
from decimal import Decimal
from app.market.core import MarketplaceCosts, find_arbitrage
from app.market.models import Listing, MarketSnapshot


def listing(marketplace: str, price: str) -> Listing:
    now = datetime.now(timezone.utc)
    return Listing(marketplace=marketplace, listing_id=f"{marketplace}-1", gift_id="gift-1", collection_id="collection-1", price_ton=Decimal(price), observed_at=now, source_url="https://example.com")


def test_arbitrage_is_net_of_fees():
    snapshots = [MarketSnapshot(marketplace="portals", observed_at=listing("portals", "10").observed_at, listings=[listing("portals", "10")], source_url="https://example.com"), MarketSnapshot(marketplace="getgems", observed_at=listing("getgems", "12").observed_at, listings=[listing("getgems", "12")], source_url="https://example.com")]
    result = find_arbitrage(snapshots, {"getgems": MarketplaceCosts(fee_percent=Decimal("2"))})
    assert len(result) == 1
    assert result[0].profit_ton == Decimal("1.76")


def test_no_opportunity_when_fee_erases_spread():
    now = datetime.now(timezone.utc)
    snapshots = [MarketSnapshot(marketplace="portals", observed_at=now, listings=[listing("portals", "10")], source_url="https://example.com"), MarketSnapshot(marketplace="getgems", observed_at=now, listings=[listing("getgems", "10.1")], source_url="https://example.com")]
    assert find_arbitrage(snapshots, {"getgems": MarketplaceCosts(fee_percent=Decimal("2"))}) == []
