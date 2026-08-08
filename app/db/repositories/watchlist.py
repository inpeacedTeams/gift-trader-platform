from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, Listing, WatchlistItem


class WatchlistRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def cards(self, user_id: int) -> list[dict]:
        """Saved gifts with their live price.

        Aggregating here keeps the saved list honest: a gift whose listings
        all disappeared shows no floor instead of a stale one.
        """
        rows = (
            await self.session.execute(
                select(
                    Gift.id,
                    Gift.canonical_id,
                    Gift.name,
                    Gift.model,
                    Gift.gift_number,
                    Gift.image_url,
                    Gift.collection_id,
                    Collection.name.label("collection_name"),
                    func.min(Listing.price_ton).label("floor_ton"),
                    func.percentile_cont(0.5)
                    .within_group(Listing.price_ton.asc())
                    .label("median_ton"),
                    func.count(Listing.id).label("listings_count"),
                    WatchlistItem.created_at,
                )
                .join(WatchlistItem, WatchlistItem.gift_id == Gift.id)
                .outerjoin(Listing, (Listing.gift_id == Gift.id) & Listing.active.is_(True))
                .outerjoin(Collection, Collection.id == Gift.collection_id)
                .where(WatchlistItem.user_id == user_id)
                .group_by(Gift.id, Collection.name, WatchlistItem.created_at)
                .order_by(WatchlistItem.created_at.desc())
            )
        ).all()
        return [
            {
                "id": row.id,
                "canonical_id": row.canonical_id,
                "collection_id": row.collection_id,
                "collection_name": row.collection_name,
                "name": row.name,
                "model": row.model,
                "gift_number": row.gift_number,
                "image_url": row.image_url,
                "floor_ton": row.floor_ton,
                "median_ton": Decimal(row.median_ton) if row.median_ton is not None else None,
                "listings_count": int(row.listings_count or 0),
                "saved_at": row.created_at,
            }
            for row in rows
        ]

    async def best_venues(self, gift_ids: list[int]) -> dict[int, str]:
        if not gift_ids:
            return {}
        rows = (
            await self.session.execute(
                select(Listing.gift_id, Listing.marketplace)
                .where(Listing.gift_id.in_(gift_ids), Listing.active.is_(True))
                .distinct(Listing.gift_id)
                .order_by(Listing.gift_id, Listing.price_ton.asc())
            )
        ).all()
        return {gift_id: marketplace for gift_id, marketplace in rows}
