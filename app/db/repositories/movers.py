from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Numeric, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, Listing, PriceSnapshot


class MoversRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def movers(self, *, hours: int = 24, limit: int = 5) -> dict[str, list[dict]]:
        """Biggest floor moves inside the window.

        The opening and closing floor come from the first and last snapshot
        recorded for each gift, so a gift that only appeared mid window is
        compared against its own first reading rather than against nothing.
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        window = (
            select(
                PriceSnapshot.gift_id.label("gift_id"),
                func.min(PriceSnapshot.observed_at).label("opened_at"),
                func.max(PriceSnapshot.observed_at).label("closed_at"),
            )
            .where(PriceSnapshot.observed_at >= since, PriceSnapshot.floor_ton.is_not(None))
            .group_by(PriceSnapshot.gift_id)
            .subquery()
        )
        opening = PriceSnapshot.__table__.alias("opening")
        closing = PriceSnapshot.__table__.alias("closing")
        change = cast(
            (closing.c.floor_ton - opening.c.floor_ton) / opening.c.floor_ton * 100,
            Numeric(8, 2),
        ).label("change_percent")
        query = (
            select(
                Gift.id,
                Gift.name,
                Gift.model,
                Gift.image_url,
                Gift.collection_id,
                Collection.name.label("collection_name"),
                opening.c.floor_ton.label("opening_ton"),
                closing.c.floor_ton.label("closing_ton"),
                change,
            )
            .select_from(window)
            .join(
                opening,
                and_(
                    opening.c.gift_id == window.c.gift_id,
                    opening.c.observed_at == window.c.opened_at,
                ),
            )
            .join(
                closing,
                and_(
                    closing.c.gift_id == window.c.gift_id,
                    closing.c.observed_at == window.c.closed_at,
                ),
            )
            .join(Gift, Gift.id == window.c.gift_id)
            .outerjoin(Collection, Collection.id == Gift.collection_id)
            .where(
                opening.c.floor_ton > 0,
                closing.c.floor_ton != opening.c.floor_ton,
                # Only gifts that can still be traded right now.
                select(Listing.id)
                .where(Listing.gift_id == Gift.id, Listing.active.is_(True))
                .exists(),
            )
            .distinct(window.c.gift_id)
        )
        rows = (await self.session.execute(query)).all()
        items = [
            {
                "gift_id": row.id,
                "name": row.name,
                "model": row.model,
                "image_url": row.image_url,
                "collection_id": row.collection_id,
                "collection_name": row.collection_name,
                "floor_ton": row.closing_ton,
                "previous_ton": row.opening_ton,
                "change_percent": row.change_percent,
            }
            for row in rows
        ]
        gainers = sorted(
            (item for item in items if Decimal(item["change_percent"]) > 0),
            key=lambda item: Decimal(item["change_percent"]),
            reverse=True,
        )
        losers = sorted(
            (item for item in items if Decimal(item["change_percent"]) < 0),
            key=lambda item: Decimal(item["change_percent"]),
        )
        return {"gainers": gainers[:limit], "losers": losers[:limit]}
