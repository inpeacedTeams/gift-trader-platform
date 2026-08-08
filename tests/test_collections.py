from datetime import datetime, timezone
from decimal import Decimal

from app.market.identity import collection_key, slugify
from app.market.models import Listing


def listing(**overrides) -> Listing:
    payload = {
        "marketplace": "tonnel",
        "listing_id": "1",
        "gift_id": "1",
        "price_ton": Decimal("10"),
        "observed_at": datetime.now(timezone.utc),
        "source_url": "https://market.tonnel.network/",
    }
    payload.update(overrides)
    return Listing(**payload)


def test_slugify_builds_a_stable_series_key():
    assert slugify("Snoop Dogg") == "snoop-dogg"
    assert slugify("  Snoop   Dogg ") == "snoop-dogg"
    assert slugify(None) == ""


def test_same_series_from_different_marketplaces_shares_one_key():
    tonnel = listing(collection_name="Snoop Dogg", name="Snoop Dogg", model="Golden")
    portals = listing(marketplace="portals", collection_name="snoop dogg", model="Silver")

    assert collection_key(tonnel)[0] == collection_key(portals)[0] == "slug:snoop-dogg"


def test_chain_address_wins_over_name():
    onchain = listing(collection_id="EQCollectionAddress", collection_name="Snoop Dogg")

    key, name = collection_key(onchain)

    assert key == "eqcollectionaddress"
    assert name == "Snoop Dogg"


def test_listing_without_any_name_has_no_collection():
    assert collection_key(listing()) is None
