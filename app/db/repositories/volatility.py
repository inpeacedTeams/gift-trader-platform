"""How jumpy a gift's price is.

A floor is only worth quoting if it holds. Two gifts can sit at the same
price while one has not moved in a week and the other swings twenty percent
between crawls, and those are completely different trades: the calm one can
be planned around, the wild one is a position that needs watching.

Everything here is measured from observations we actually stored. No model,
no annualisation of thin data, and an explicit "unknown" when the series is
too short to say anything honest.
"""

import statistics
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MarketEvent, PriceSnapshot

CENT = Decimal("0.01")
DEFAULT_WINDOW_DAYS = 14
# Below this the standard deviation is an accident of when we happened to look.
MIN_SAMPLES = 6
# Daily move spread, in percent. Chosen to match how these markets read: a
# few percent a day is ordinary, twenty is a gift in the middle of something.
TIERS: tuple[tuple[Decimal, str], ...] = (
    (Decimal("3"), "calm"),
    (Decimal("8"), "normal"),
    (Decimal("20"), "active"),
)
WILD = "wild"
UNKNOWN = "unknown"


def _label(daily_percent: Decimal | None) -> str:
    if daily_percent is None:
        return UNKNOWN
    for bound, name in TIERS:
        if daily_percent <= bound:
            return name
    return WILD


class VolatilityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def for_gift(self, gift_id: int, window_days: int = DEFAULT_WINDOW_DAYS) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        # One point per crawl: the cheapest floor across every venue, which is
        # the price a buyer would actually have paid at that moment.
        rows = (
            await self.session.execute(
                select(
                    PriceSnapshot.observed_at,
                    func.min(PriceSnapshot.floor_ton).label("floor"),
                )
                .where(
                    PriceSnapshot.gift_id == gift_id,
                    PriceSnapshot.observed_at >= cutoff,
                    PriceSnapshot.floor_ton.is_not(None),
                )
                .group_by(PriceSnapshot.observed_at)
                .order_by(PriceSnapshot.observed_at.asc())
            )
        ).all()
        moves = await self.session.scalar(
            select(func.count(MarketEvent.id)).where(
                MarketEvent.gift_id == gift_id,
                MarketEvent.occurred_at >= cutoff,
                MarketEvent.event_type.in_(("price_up", "price_down")),
            )
        )
        return self._describe(rows, moves or 0, window_days)

    def _describe(self, rows: list, moves: int, window_days: int) -> dict:
        prices = [Decimal(row.floor) for row in rows if row.floor and row.floor > 0]
        observed_days = (
            (rows[-1].observed_at - rows[0].observed_at).total_seconds() / 86400 if len(rows) > 1 else 0
        )
        base = {
            "window_days": window_days,
            "samples": len(prices),
            "observed_days": round(observed_days, 2),
            "price_changes": moves,
            "changes_per_day": round(moves / observed_days, 2) if observed_days >= 1 else None,
            "low_ton": min(prices) if prices else None,
            "high_ton": max(prices) if prices else None,
            "range_percent": None,
            "daily_percent": None,
            "max_move_percent": None,
            "max_drawdown_percent": None,
            "confident": False,
            "label": UNKNOWN,
        }
        if len(prices) < 2:
            return base

        low, high = min(prices), max(prices)
        base["range_percent"] = ((high - low) / low * Decimal(100)).quantize(
            CENT, rounding=ROUND_HALF_UP
        )
        returns = [
            (prices[index] - prices[index - 1]) / prices[index - 1] * Decimal(100)
            for index in range(1, len(prices))
        ]
        base["max_move_percent"] = max(abs(value) for value in returns).quantize(
            CENT, rounding=ROUND_HALF_UP
        )
        base["max_drawdown_percent"] = self._drawdown(prices)

        if len(prices) < MIN_SAMPLES or observed_days <= 0:
            return base
        spread = Decimal(str(statistics.pstdev([float(value) for value in returns])))
        # Observations are not evenly spaced, so scale the per observation
        # spread by how many we see in a day. Square root because independent
        # moves add in variance, not in size.
        per_day = Decimal(len(returns)) / Decimal(str(observed_days))
        daily = (spread * Decimal(str(float(per_day) ** 0.5))).quantize(
            CENT, rounding=ROUND_HALF_UP
        )
        base["daily_percent"] = daily
        base["confident"] = True
        base["label"] = _label(daily)
        return base

    @staticmethod
    def _drawdown(prices: list[Decimal]) -> Decimal:
        """Worst peak to trough fall in the window.

        This is the number that matters to somebody holding: not how wide the
        range was, but how far it fell from the best moment to sell.
        """
        peak = prices[0]
        worst = Decimal(0)
        for price in prices:
            peak = max(peak, price)
            fall = (peak - price) / peak * Decimal(100)
            worst = max(worst, fall)
        return worst.quantize(CENT, rounding=ROUND_HALF_UP)
