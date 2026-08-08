from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, Listing
from app.market.identity import canonical_collection_key, slugify
from app.market.models import Listing as SourceListing


class CollectionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def resolve(self, item: SourceListing) -> Collection | None:
        """Find or create the collection a listing belongs to."""
        key = canonical_collection_key(item)
        if key is None:
            return None
        name = item.collection_name or item.name
        collection = await self.session.scalar(
            select(Collection).where(Collection.chain_address == key)
        )
        if collection is None:
            collection = Collection(chain_address=key, name=name, slug=slugify(name))
            self.session.add(collection)
            await self.session.flush()
        elif name and not collection.name:
            collection.name = name
            collection.slug = slugify(name)
        return collection

    def _base(self, search: str | None) -> Select:
        """Collection rows with live aggregates over active listings."""
        statement = (
            select(
                Collection.id,
                Collection.name,
                Collection.slug,
                Collection.chain_address,
                func.count(func.distinct(Gift.id)).label("gift_count"),
                func.count(Listing.id).label("listings_count"),
                func.min(Listing.price_ton).label("floor_ton"),
                func.max(Gift.image_url).label("image_url"),
            )
            .join(Gift, Gift.collection_id == Collection.id)
            .outerjoin(Listing, (Listing.gift_id == Gift.id) & Listing.active.is_(True))
            .where(Gift.is_active.is_(True))
            .group_by(Collection.id, Collection.name, Collection.slug, Collection.chain_address)
        )
        if search:
            statement = statement.where(Collection.name.ilike(f"%{search}%"))
        return statement

    async def page(self, *, page: int, page_size: int, search: str | None = None):
        base = self._base(search)
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        rows = (
            await self.session.execute(
                base.order_by(func.count(Listing.id).desc(), Collection.name.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return rows, int(total or 0)

    async def detail(self, collection_id: int):
        return (await self.session.execute(self._base(None).having(Collection.id == collection_id))).first()
