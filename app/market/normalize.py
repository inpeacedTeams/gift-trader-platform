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
    groups: dict[tuple[str, str], list[Listing]] = defaultdict(list)
    rejected = 0
    for listing in snapshot.listings:
        key = canonical_gift_key(listing)
        if key.startswith("unresolved:"):
            rejected += 1
            continue
        groups[(key, listing.marketplace)].append(listing)
    normalized: list[NormalizedListing] = []
    duplicates = 0
    for (key, _), items in groups.items():
        winner = min(items, key=lambda item: (item.price_ton, item.observed_at, item.listing_id))
        duplicates += max(0, len(items) - 1)
        normalized.append(NormalizedListing(winner, key, len(items)))
    return NormalizedSnapshot(snapshot.marketplace, snapshot.observed_at, normalized, duplicates, rejected)

def aggregate_prices(items: list[NormalizedListing]) -> tuple[Decimal | None, Decimal | None, int]:
    prices = sorted(item.listing.price_ton for item in items)
    if not prices:
        return None, None, 0
    return prices[0], prices[len(prices) // 2], len(prices)
