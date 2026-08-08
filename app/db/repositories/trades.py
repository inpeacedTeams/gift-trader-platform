from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Gift, Trade
from app.market.history import Trade as TradeRecord
from app.market.history import trade_identity


class TradeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def persist(self, trades: list[TradeRecord]) -> int:
        """Store sales, skipping ones already recorded.

        Sales are immutable, so a conflict on the marketplace id means we
        have seen this trade before and can move on.
        """
        stored = 0
        for record in trades:
            gift_id = await self._gift_id(record)
            if gift_id is None:
                continue
            statement = (
                insert(Trade)
                .values(
                    gift_id=gift_id,
                    marketplace=record.marketplace,
                    external_id=record.external_id,
                    price_ton=record.price_ton,
                    seller=record.seller,
                    buyer=record.buyer,
                    traded_at=record.traded_at,
                    source_url=str(record.source_url),
                )
                .on_conflict_do_nothing(constraint="uq_trade_source_id")
                .returning(Trade.id)
            )
            if (await self.session.scalar(statement)) is not None:
                stored += 1
        await self.session.commit()
        return stored

    async def _gift_id(self, record: TradeRecord) -> int | None:
        key = trade_identity(record)
        if key.startswith("unresolved:"):
            return None
        return await self.session.scalar(select(Gift.id).where(Gift.canonical_id == key))

    async def recent(self, gift_id: int, limit: int = 20) -> list[Trade]:
        rows = await self.session.scalars(
            select(Trade)
            .where(Trade.gift_id == gift_id)
            .order_by(Trade.traded_at.desc())
            .limit(limit)
        )
        return list(rows.all())

    async def stats(self, gift_id: int, days: int = 30) -> dict:
        """What the market actually paid, not what sellers asked."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        row = (
            await self.session.execute(
                select(
                    func.count(Trade.id),
                    func.min(Trade.price_ton),
                    func.max(Trade.price_ton),
                    func.percentile_cont(0.5).within_group(Trade.price_ton.asc()),
                    func.sum(Trade.price_ton),
                    func.max(Trade.traded_at),
                ).where(Trade.gift_id == gift_id, Trade.traded_at >= since)
            )
        ).first()
        count, low, high, median, volume, last = row
        return {
            "window_days": days,
            "sales_count": int(count or 0),
            "lowest_ton": low,
            "highest_ton": high,
            "median_ton": median if median is None else Decimal(median),
            "volume_ton": volume,
            "last_sold_at": last,
        }
