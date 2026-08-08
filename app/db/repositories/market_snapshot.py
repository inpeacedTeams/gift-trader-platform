from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Gift, Listing, MarketEvent, PriceSnapshot
from app.db.repositories.collections import CollectionRepository
from app.market.identity import collection_key
from app.market.models import MarketSnapshot
from app.market.normalize import normalize_snapshot

# Rounding noise is not a price change worth telling anyone about.
MIN_CHANGE_PERCENT = Decimal("0.5")


@dataclass
class PersistResult:
    listings: int = 0
    # Which gifts this pass touched, so alerts only re-check what moved.
    gift_ids: set[int] = field(default_factory=set)


class MarketSnapshotRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.collections = CollectionRepository(session)

    async def persist(self, snapshot: MarketSnapshot) -> PersistResult:
        """Store a full pass over one marketplace and log what changed.

        Existing rows are loaded up front: a whole market crawl is tens of
        thousands of listings, and a query per listing would make the pass
        slower than the interval between passes.
        """
        now = datetime.now(timezone.utc)
        normalized = normalize_snapshot(snapshot)
        grouped: dict[str, list] = defaultdict(list)
        for item in normalized.listings:
            grouped[item.gift_key].append(item.listing)

        existing = await self._existing_listings(snapshot.marketplace)
        result = PersistResult()
        for key, listings in grouped.items():
            gift = await self._get_or_create_gift(key, listings[0])
            result.gift_ids.add(gift.id)
            prices = [item.price_ton for item in listings]
            self.session.add(
                PriceSnapshot(
                    gift_id=gift.id,
                    marketplace=snapshot.marketplace,
                    observed_at=snapshot.observed_at,
                    floor_ton=min(prices),
                    median_ton=sorted(prices)[len(prices) // 2],
                    volume_ton=None,
                    listings_count=len(listings),
                    source_url=str(snapshot.source_url),
                )
            )
            for item in listings:
                listing = existing.get(item.listing_id)
                if listing is None:
                    listing = Listing(
                        gift_id=gift.id,
                        marketplace=item.marketplace,
                        external_id=item.listing_id,
                        price_ton=item.price_ton,
                        seller=item.seller,
                        url=str(item.url) if item.url else None,
                        first_seen_at=item.observed_at,
                        last_seen_at=item.observed_at,
                        active=True,
                    )
                    self.session.add(listing)
                    await self.session.flush()
                    existing[item.listing_id] = listing
                    self._record(gift.id, listing, "listed", item.price_ton, None, now)
                else:
                    previous = listing.price_ton
                    reappeared = not listing.active
                    listing.gift_id = gift.id
                    listing.price_ton = item.price_ton
                    listing.seller = item.seller
                    listing.url = str(item.url) if item.url else listing.url
                    listing.last_seen_at = item.observed_at
                    listing.active = True
                    if reappeared:
                        self._record(gift.id, listing, "listed", item.price_ton, None, now)
                    else:
                        self._maybe_price_event(gift.id, listing, previous, item.price_ton, now)
                result.listings += 1
            await self.session.flush()

        result.gift_ids |= await self._close_missing(snapshot.marketplace, now)
        await self.session.commit()
        return result

    async def _existing_listings(self, marketplace: str) -> dict[str, Listing]:
        rows = await self.session.scalars(
            select(Listing).where(Listing.marketplace == marketplace)
        )
        return {row.external_id: row for row in rows.all()}

    def _record(
        self,
        gift_id: int,
        listing: Listing,
        event_type: str,
        price: Decimal | None,
        previous: Decimal | None,
        occurred_at: datetime,
        change_percent: Decimal | None = None,
    ) -> None:
        self.session.add(
            MarketEvent(
                gift_id=gift_id,
                listing_id=listing.id,
                marketplace=listing.marketplace,
                event_type=event_type,
                price_ton=price,
                previous_ton=previous,
                change_percent=change_percent,
                occurred_at=occurred_at,
            )
        )

    def _maybe_price_event(
        self,
        gift_id: int,
        listing: Listing,
        previous: Decimal | None,
        current: Decimal,
        occurred_at: datetime,
    ) -> None:
        if previous is None or previous <= 0 or previous == current:
            return
        change = (current - previous) / previous * Decimal(100)
        if abs(change) < MIN_CHANGE_PERCENT:
            return
        self._record(
            gift_id,
            listing,
            "price_up" if change > 0 else "price_down",
            current,
            previous,
            occurred_at,
            change_percent=change.quantize(Decimal("0.01")),
        )

    async def _close_missing(self, marketplace: str, now: datetime) -> set[int]:
        """Anything not seen in this pass is gone from the market."""
        stale = (
            await self.session.scalars(
                select(Listing).where(
                    Listing.marketplace == marketplace,
                    Listing.active.is_(True),
                    Listing.last_seen_at < now,
                )
            )
        ).all()
        for listing in stale:
            self._record(listing.gift_id, listing, "delisted", listing.price_ton, None, now)
        if stale:
            await self.session.execute(
                update(Listing)
                .where(Listing.id.in_([item.id for item in stale]))
                .values(active=False)
            )
        return {listing.gift_id for listing in stale}

    async def _collection_id(self, item) -> int | None:
        identity = collection_key(item)
        if identity is None:
            return None
        key, name = identity
        collection = await self.collections.get_or_create(key, name)
        return collection.id

    async def _get_or_create_gift(self, key: str, item) -> Gift:
        image_url = str(item.image_url) if item.image_url else None
        gift = await self.session.scalar(select(Gift).where(Gift.canonical_id == key))
        collection_id = await self._collection_id(item)
        if gift is None:
            gift = Gift(
                canonical_id=key,
                collection_id=collection_id,
                gift_number=item.gift_number,
                name=item.name,
                model=item.model,
                image_url=image_url,
            )
            self.session.add(gift)
            await self.session.flush()
        else:
            gift.name = item.name or gift.name
            gift.model = item.model or gift.model
            gift.image_url = gift.image_url or image_url
            gift.collection_id = gift.collection_id or collection_id
            gift.gift_number = gift.gift_number if gift.gift_number is not None else item.gift_number
        return gift
