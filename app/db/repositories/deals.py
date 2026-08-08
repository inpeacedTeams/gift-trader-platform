from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, Listing

MIN_PEERS = 3


class DealRepository:
    """Finds listings priced below their own peer group.

    A gift is only comparable to the same model inside the same collection:
    a rare model is not overpriced just because a common one is cheaper.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _peer_medians(self):
        return (
            select(
                Gift.collection_id.label("collection_id"),
                Gift.model.label("model"),
                func.percentile_cont(0.5)
                .within_group(Listing.price_ton.asc())
                .label("median_ton"),
                func.count(Listing.id).label("peer_count"),
            )
            .join(Listing, (Listing.gift_id == Gift.id) & Listing.active.is_(True))
            .where(Gift.collection_id.is_not(None), Gift.model.is_not(None))
            .group_by(Gift.collection_id, Gift.model)
            .having(func.count(Listing.id) >= MIN_PEERS)
            .subquery()
        )

    async def deals(
        self,
        *,
        min_discount_percent: Decimal = Decimal(10),
        collection_id: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        peers = self._peer_medians()
        discount = (peers.c.median_ton - Listing.price_ton) / peers.c.median_ton * 100
        statement = (
            select(
                Gift.id.label("gift_id"),
                Gift.name,
                Gift.model,
                Gift.gift_number,
                Gift.image_url,
                Gift.collection_id,
                Collection.name.label("collection_name"),
                Listing.marketplace,
                Listing.price_ton,
                Listing.url,
                peers.c.median_ton,
                peers.c.peer_count,
                discount.label("discount_percent"),
            )
            .join(Listing, (Listing.gift_id == Gift.id) & Listing.active.is_(True))
            .join(
                peers,
                (peers.c.collection_id == Gift.collection_id) & (peers.c.model == Gift.model),
            )
            .outerjoin(Collection, Collection.id == Gift.collection_id)
            .where(discount >= min_discount_percent)
            .order_by(discount.desc())
            .limit(limit)
        )
        if collection_id is not None:
            statement = statement.where(Gift.collection_id == collection_id)
        rows = (await self.session.execute(statement)).all()
        return [
            {
                "gift_id": row.gift_id,
                "name": row.name,
                "model": row.model,
                "gift_number": row.gift_number,
                "image_url": row.image_url,
                "collection_id": row.collection_id,
                "collection_name": row.collection_name,
                "marketplace": row.marketplace,
                "price_ton": row.price_ton,
                "median_ton": row.median_ton,
                "peer_count": int(row.peer_count or 0),
                "discount_percent": row.discount_percent,
                "url": row.url,
            }
            for row in rows
        ]
