from datetime import datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import PriceSnapshot

class PriceHistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(self, *, gift_id: int, marketplace: str, observed_at: datetime, floor_ton: Decimal | None, median_ton: Decimal | None, volume_ton: Decimal | None, listings_count: int, source_url: str | None) -> PriceSnapshot:
        snapshot = PriceSnapshot(gift_id=gift_id, marketplace=marketplace, observed_at=observed_at, floor_ton=floor_ton, median_ton=median_ton, volume_ton=volume_ton, listings_count=listings_count, source_url=source_url)
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def history(self, *, gift_id: int, marketplace: str | None = None, limit: int = 500) -> list[PriceSnapshot]:
        stmt = select(PriceSnapshot).where(PriceSnapshot.gift_id == gift_id)
        if marketplace:
            stmt = stmt.where(PriceSnapshot.marketplace == marketplace)
        stmt = stmt.order_by(PriceSnapshot.observed_at.desc()).limit(limit)
        return list((await self.session.scalars(stmt)).all())
