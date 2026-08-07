from datetime import datetime, timezone
from decimal import Decimal
from app.market.models import Listing, MarketSnapshot
from app.market.normalize import normalize_snapshot


def listing(source: str, listing_id: str, price: str, canonical: str | None = "gift-address") -> Listing:
    return Listing(marketplace=source, listing_id=listing_id, gift_id=listing_id, canonical_id=canonical, price_ton=Decimal(price), observed_at=datetime.now(timezone.utc), source_url="https://example.com")


def test_keeps_cheapest_listing_per_gift_and_marketplace():
    snapshot = MarketSnapshot(marketplace="portals", observed_at=datetime.now(timezone.utc), listings=[listing("portals", "a", "12"), listing("portals", "b", "10")], source_url="https://example.com")
    result = normalize_snapshot(snapshot)
    assert len(result.listings) == 1
    assert result.listings[0].listing.listing_id == "b"
    assert result.duplicate_count == 1


def test_rejects_unresolved_identity():
    snapshot = MarketSnapshot(marketplace="fragment", observed_at=datetime.now(timezone.utc), listings=[listing("fragment", "a", "12", None)], source_url="https://example.com")
    result = normalize_snapshot(snapshot)
    assert result.listings == []
    assert result.rejected_count == 1
