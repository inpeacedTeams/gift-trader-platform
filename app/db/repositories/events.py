from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, MarketEvent

EVENT_TYPES = ("listed", "price_down", "price_up", "delisted")


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def feed(
        self,
        *,
        limit: int = 40,
        after_id: int | None = None,
        event_type: str | None = None,
        gift_id: int | None = None,
    ) -> list[dict]:
        """Newest changes first.

        `after_id` lets a poller ask only for what appeared since its last
        call, which keeps the feed cheap enough to refresh every few seconds.
        """
        statement = (
            select(
                MarketEvent.id,
                MarketEvent.gift_id,
                MarketEvent.marketplace,
                MarketEvent.event_type,
                MarketEvent.price_ton,
                MarketEvent.previous_ton,
                MarketEvent.change_percent,
                MarketEvent.occurred_at,
                Gift.name,
                Gift.model,
                Gift.image_url,
                Collection.name.label("collection_name"),
            )
            .join(Gift, Gift.id == MarketEvent.gift_id)
            .outerjoin(Collection, Collection.id == Gift.collection_id)
            .order_by(MarketEvent.id.desc())
            .limit(limit)
        )
        if after_id is not None:
            statement = statement.where(MarketEvent.id > after_id)
        if event_type:
            statement = statement.where(MarketEvent.event_type == event_type)
        if gift_id is not None:
            statement = statement.where(MarketEvent.gift_id == gift_id)
        rows = (await self.session.execute(statement)).all()
        return [
            {
                "id": row.id,
                "gift_id": row.gift_id,
                "name": row.name,
                "model": row.model,
                "image_url": row.image_url,
                "collection_name": row.collection_name,
                "marketplace": row.marketplace,
                "event_type": row.event_type,
                "price_ton": row.price_ton,
                "previous_ton": row.previous_ton,
                "change_percent": row.change_percent,
                "occurred_at": row.occurred_at,
            }
            for row in rows
        ]
