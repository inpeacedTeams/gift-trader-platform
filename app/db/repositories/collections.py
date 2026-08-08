from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, Listing


class CollectionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, key: str, name: str | None) -> Collection:
        collection = await self.session.scalar(
            select(Collection).where(Collection.chain_address == key)
        )
        if collection is None:
            collection = Collection(chain_address=key, name=name, slug=key.removeprefix("slug:"))
            self.session.add(collection)
            await self.session.flush()
        elif name and not collection.name:
            collection.name = name
        return collection

    async def overview(self, *, search: str | None = None) -> list[dict]:
        """Every tracked series with live floor and depth.

        Aggregated over active listings so an empty series never shows a
        stale floor.
        """
        query = (
            select(
                Collection.id,
                Collection.name,
                Collection.slug,
                Collection.chain_address,
                func.count(distinct(Gift.id)).label("gift_count"),
                func.min(Listing.price_ton).label("floor_ton"),
                func.count(Listing.id).label("listings_count"),
                func.min(Gift.image_url).label("image_url"),
            )
            .join(Gift, Gift.collection_id == Collection.id)
            .outerjoin(Listing, (Listing.gift_id == Gift.id) & Listing.active.is_(True))
            .group_by(Collection.id)
            .order_by(func.count(Listing.id).desc(), Collection.name.asc())
        )
        if search:
            query = query.where(Collection.name.ilike(f"%{search}%"))
        rows = (await self.session.execute(query)).all()
        return [
            {
                "id": row.id,
                "name": row.name or row.slug or row.chain_address,
                "slug": row.slug,
                "chain_address": row.chain_address,
                "gift_count": int(row.gift_count or 0),
                "listings_count": int(row.listings_count or 0),
                "floor_ton": row.floor_ton,
                "image_url": row.image_url,
            }
            for row in rows
        ]
