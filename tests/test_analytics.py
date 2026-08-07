from datetime import datetime, timezone
from decimal import Decimal
from app.market.analytics import analyze_snapshot, overview
from app.market.models import Listing, MarketSnapshot

def test_overview_calculates_floor_volume_and_confidence():
    now = datetime.now(timezone.utc)
    snapshot = MarketSnapshot(marketplace="portals", observed_at=now, source_url="https://example.com", listings=[Listing(marketplace="portals", listing_id="1", gift_id="1", canonical_id="chain:1", price_ton=Decimal("10"), observed_at=now, source_url="https://example.com"), Listing(marketplace="portals", listing_id="2", gift_id="2", price_ton=Decimal("20"), observed_at=now, source_url="https://example.com")])
    metrics = analyze_snapshot(snapshot)
    assert metrics.floor_ton == Decimal("10")
    assert metrics.volume_ton == Decimal("30")
    assert metrics.data_confidence == Decimal("50")
    assert overview([snapshot]).total_listings == 2
