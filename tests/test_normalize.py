from datetime import datetime, timezone
from decimal import Decimal

from app.market.models import Listing, MarketSnapshot
from app.market.normalize import normalize_snapshot


def listing(
    source: str, listing_id: str, price: str, canonical: str | None = "gift-address"
) -> Listing:
    return Listing(
        marketplace=source,
        listing_id=listing_id,
        gift_id=listing_id,
        canonical_id=canonical,
        price_ton=Decimal(price),
        observed_at=datetime.now(timezone.utc),
        source_url="https://example.com",
    )


def snapshot(*listings: Listing, marketplace: str = "portals") -> MarketSnapshot:
    return MarketSnapshot(
        marketplace=marketplace,
        observed_at=datetime.now(timezone.utc),
        listings=list(listings),
        source_url="https://example.com",
    )


def test_keeps_every_listing_so_market_depth_stays_real():
    result = normalize_snapshot(
        snapshot(listing("portals", "a", "12"), listing("portals", "b", "10"))
    )

    assert [item.listing.listing_id for item in result.listings] == ["b", "a"]
    assert {item.duplicate_count for item in result.listings} == {2}
    assert result.duplicate_count == 0


def test_drops_repeated_listing_id_from_same_source():
    result = normalize_snapshot(
        snapshot(listing("portals", "a", "12"), listing("portals", "a", "12"))
    )

    assert len(result.listings) == 1
    assert result.duplicate_count == 1


def test_rejects_unresolved_identity():
    result = normalize_snapshot(
        snapshot(listing("fragment", "a", "12", None), marketplace="fragment")
    )

    assert result.listings == []
    assert result.rejected_count == 1
