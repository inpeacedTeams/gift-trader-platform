from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Gift, Listing, PriceSnapshot

class GiftRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def page(self, *, page: int, page_size: int, search: str | None = None, marketplace: str | None = None, active_only: bool = True):
        base = select(Gift).where(Gift.is_active.is_(True)) if active_only else select(Gift)
        if search:
            pattern = f"%{search}%"
            base = base.where(or_(Gift.name.ilike(pattern), Gift.model.ilike(pattern), Gift.canonical_id.ilike(pattern)))
        if marketplace:
            base = base.join(Listing, Listing.gift_id == Gift.id).where(Listing.marketplace == marketplace, Listing.active.is_(True)).distinct()
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        gifts = list((await self.session.scalars(base.order_by(Gift.id.desc()).offset((page - 1) * page_size).limit(page_size))).all())
        return gifts, int(total or 0)

    async def detail(self, gift_id: int):
        gift = await self.session.get(Gift, gift_id)
        if gift is None:
            return None
        listings = list((await self.session.scalars(select(Listing).where(Listing.gift_id == gift_id).order_by(Listing.price_ton.asc()))).all())
        return gift, listings

    async def latest_stats(self, gift_id: int):
        return list((await self.session.scalars(select(PriceSnapshot).where(PriceSnapshot.gift_id == gift_id).order_by(PriceSnapshot.observed_at.desc()).limit(100))).all())
