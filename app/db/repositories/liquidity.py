from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Listing, Trade

WINDOW_DAYS = 30
# Below this the numbers describe two events, not a market.
MIN_OBSERVATIONS = 3


class LiquidityRepository:
    """How easily a gift can be sold again.

    A discount only pays if there is an exit. Time to sale comes from how
    long listings survive on the book, which we know because every crawl
    records when a listing disappears.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def for_gifts(self, gift_ids: list[int]) -> dict[int, dict]:
        if not gift_ids:
            return {}
        since = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
        hours_on_book = func.percentile_cont(0.5).within_group(
            cast(
                func.extract("epoch", Listing.closed_at - Listing.first_seen_at) / 3600.0,
                Float,
            ).asc()
        )
        closed = (
            await self.session.execute(
                select(
                    Listing.gift_id,
                    hours_on_book.label("median_hours"),
                    func.count(Listing.id).label("closed_count"),
                )
                .where(
                    Listing.gift_id.in_(gift_ids),
                    Listing.closed_at.is_not(None),
                    Listing.closed_at >= since,
                )
                .group_by(Listing.gift_id)
            )
        ).all()
        # Trades already carry gift_id. Joining listings here multiplied every
        # sale by the number of listings the gift has.
        sales = (
            await self.session.execute(
                select(Trade.gift_id, func.count(Trade.id))
                .where(Trade.gift_id.in_(gift_ids), Trade.traded_at >= since)
                .group_by(Trade.gift_id)
            )
        ).all()
        depth = (
            await self.session.execute(
                select(Listing.gift_id, func.count(Listing.id))
                .where(Listing.gift_id.in_(gift_ids), Listing.active.is_(True))
                .group_by(Listing.gift_id)
            )
        ).all()

        sales_by_gift = {gift_id: count for gift_id, count in sales}
        depth_by_gift = {gift_id: count for gift_id, count in depth}
        weeks = Decimal(WINDOW_DAYS) / Decimal(7)
        result: dict[int, dict] = {}
        for gift_id, median_hours, closed_count in closed:
            result[gift_id] = {
                "median_hours_to_sell": round(float(median_hours), 1) if median_hours else None,
                "closed_listings": int(closed_count or 0),
                "sales_per_week": float(round(Decimal(sales_by_gift.get(gift_id, 0)) / weeks, 2)),
                "active_depth": depth_by_gift.get(gift_id, 0),
                "confident": int(closed_count or 0) >= MIN_OBSERVATIONS,
            }
        for gift_id in gift_ids:
            result.setdefault(
                gift_id,
                {
                    "median_hours_to_sell": None,
                    "closed_listings": 0,
                    "sales_per_week": float(round(Decimal(sales_by_gift.get(gift_id, 0)) / weeks, 2)),
                    "active_depth": depth_by_gift.get(gift_id, 0),
                    "confident": False,
                },
            )
        return result

    async def floor_gap(self, gift_id: int) -> Decimal | None:
        """Distance from the cheapest listing to the next one, in percent.

        A wide gap means the floor is a single outlier: buying at it and
        reselling at it is not the same trade.
        """
        prices = (
            await self.session.scalars(
                select(Listing.price_ton)
                .where(Listing.gift_id == gift_id, Listing.active.is_(True))
                .order_by(Listing.price_ton.asc())
                .limit(2)
            )
        ).all()
        if len(prices) < 2 or not prices[0]:
            return None
        return (prices[1] - prices[0]) / prices[0] * Decimal(100)


def liquidity_label(stats: dict) -> str:
    """Plain wording, because 'score 0.62' tells a trader nothing."""
    if not stats.get("confident"):
        return "unknown"
    hours = stats.get("median_hours_to_sell")
    if hours is None:
        return "unknown"
    if hours <= 12:
        return "fast"
    if hours <= 72:
        return "steady"
    return "slow"
