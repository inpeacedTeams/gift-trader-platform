from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import PriceSnapshot

async def price_trend(session: AsyncSession, *, gift_id: int, marketplace: str | None = None, window_hours: int = 24) -> dict[str, object]:
    since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    stmt = select(PriceSnapshot).where(PriceSnapshot.gift_id == gift_id, PriceSnapshot.observed_at >= since).order_by(PriceSnapshot.observed_at.asc())
    if marketplace:
        stmt = stmt.where(PriceSnapshot.marketplace == marketplace)
    rows = list((await session.scalars(stmt)).all())
    points = [{"observed_at": row.observed_at, "marketplace": row.marketplace, "floor_ton": row.floor_ton} for row in rows if row.floor_ton is not None]
    if len(points) < 2:
        return {"direction": "insufficient_data", "change_percent": None, "points": points}
    first = Decimal(str(points[0]["floor_ton"]))
    last = Decimal(str(points[-1]["floor_ton"]))
    change = ((last - first) / first * Decimal("100")) if first else Decimal("0")
    return {"direction": "up" if change > 0 else "down" if change < 0 else "flat", "change_percent": change, "points": points}
