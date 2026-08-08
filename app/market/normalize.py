from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from .identity import canonical_gift_key
from .models import Listing, MarketSnapshot


@dataclass(frozen=True)
class NormalizedListing:
    listing: Listing
    gift_key: str
    duplicate_count: int = 1


@dataclass(frozen=True)
class NormalizedSnapshot:
    marketplace: str
    observed_at: object
    listings: list[NormalizedListing]
    duplicate_count: int
    rejected_count: int


def normalize_snapshot(snapshot: MarketSnapshot) -> NormalizedSnapshot:
    """Group listings by gift identity while keeping full market depth.

    Every distinct listing survives: five Plush Pepes on sale means five
    listings and a listings_count of five. Only the exact same listing id
    repeated by one source counts as a duplicate.
    """
    groups: dict[str, list[Listing]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    rejected = 0
    duplicates = 0
    for listing in snapshot.listings:
        key = canonical_gift_key(listing)
        if key.startswith("unresolved:"):
            rejected += 1
            continue
        identity = (listing.marketplace, listing.listing_id)
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        groups[key].append(listing)
    normalized: list[NormalizedListing] = []
    for key, items in groups.items():
        depth = len(items)
        for listing in sorted(items, key=lambda item: (item.price_ton, item.listing_id)):
            normalized.append(NormalizedListing(listing, key, depth))
    return NormalizedSnapshot(
        snapshot.marketplace, snapshot.observed_at, normalized, duplicates, rejected
    )


def aggregate_prices(
    items: list[NormalizedListing],
) -> tuple[Decimal | None, Decimal | None, int]:
    prices = sorted(item.listing.price_ton for item in items)
    if not prices:
        return None, None, 0
    return prices[0], prices[len(prices) // 2], len(prices)
