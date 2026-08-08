from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Gift, Listing, PriceSnapshot
from app.market.models import MarketSnapshot
from app.market.normalize import normalize_snapshot


class MarketSnapshotRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def persist(self, snapshot: MarketSnapshot) -> int:
        now = datetime.now(timezone.utc)
        normalized = normalize_snapshot(snapshot)
        grouped: dict[str, list] = defaultdict(list)
        for item in normalized.listings:
            grouped[item.gift_key].append(item.listing)
        persisted = 0
        for key, listings in grouped.items():
            gift = await self._get_or_create_gift(key, listings[0])
            prices = [item.price_ton for item in listings]
            floor = min(prices)
            median = sorted(prices)[len(prices) // 2]
            self.session.add(
                PriceSnapshot(
                    gift_id=gift.id,
                    marketplace=snapshot.marketplace,
                    observed_at=snapshot.observed_at,
                    floor_ton=floor,
                    median_ton=median,
                    volume_ton=None,
                    listings_count=len(listings),
                    source_url=str(snapshot.source_url),
                )
            )
            for item in listings:
                listing = await self.session.scalar(
                    select(Listing).where(
                        Listing.marketplace == item.marketplace,
                        Listing.external_id == item.listing_id,
                    )
                )
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
                else:
                    listing.gift_id = gift.id
                    listing.price_ton = item.price_ton
                    listing.seller = item.seller
                    listing.url = str(item.url) if item.url else listing.url
                    listing.last_seen_at = item.observed_at
                    listing.active = True
                persisted += 1
            await self.session.flush()
        await self.session.execute(
            update(Listing)
            .where(
                Listing.marketplace == snapshot.marketplace,
                Listing.last_seen_at < now,
            )
            .values(active=False)
        )
        await self.session.commit()
        return persisted

    async def _get_or_create_gift(self, key: str, item) -> Gift:
        image_url = str(item.image_url) if item.image_url else None
        gift = await self.session.scalar(select(Gift).where(Gift.canonical_id == key))
        if gift is None:
            gift = Gift(
                canonical_id=key,
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
            gift.gift_number = gift.gift_number if gift.gift_number is not None else item.gift_number
        return gift
