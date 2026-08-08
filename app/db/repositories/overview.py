from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, Listing, MarketEvent, SourceStatus, Trade


class OverviewRepository:
    """Headline numbers for the dashboard, straight from stored rows."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def stats(self) -> dict:
        listings = await self.session.scalar(
            select(func.count(Listing.id)).where(Listing.active.is_(True))
        )
        gifts = await self.session.scalar(
            select(func.count(func.distinct(Listing.gift_id))).where(Listing.active.is_(True))
        )
        collections = await self.session.scalar(select(func.count(Collection.id)))
        floor_total = await self.session.scalar(
            select(func.sum(Listing.price_ton)).where(Listing.active.is_(True))
        )
        sources_online = await self.session.scalar(
            select(func.count(SourceStatus.id)).where(SourceStatus.status == "ok")
        )
        last_sync = await self.session.scalar(select(func.max(SourceStatus.last_success_at)))
        day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        events_24h = await self.session.scalar(
            select(func.count(MarketEvent.id)).where(MarketEvent.occurred_at >= day_ago)
        )
        sales_24h = await self.session.scalar(
            select(func.count(Trade.id)).where(Trade.traded_at >= day_ago)
        )
        tracked_gifts = await self.session.scalar(select(func.count(Gift.id)))
        return {
            "active_listings": int(listings or 0),
            "listed_gifts": int(gifts or 0),
            "tracked_gifts": int(tracked_gifts or 0),
            "collections": int(collections or 0),
            "market_value_ton": Decimal(floor_total) if floor_total is not None else None,
            "sources_online": int(sources_online or 0),
            "events_24h": int(events_24h or 0),
            "sales_24h": int(sales_24h or 0),
            "last_sync_at": last_sync,
        }
