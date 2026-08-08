from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Gift
from app.db.repositories import VolatilityRepository
from app.db.session import get_session

router = APIRouter(prefix="/volatility", tags=["volatility"])


class GiftVolatility(BaseModel):
    """How much the floor moves, and how often.

    `confident` is false while the series is too short to mean anything, so
    the interface can say "not enough observations" instead of printing a
    precise number derived from three data points.
    """

    window_days: int
    samples: int
    observed_days: float
    price_changes: int
    changes_per_day: float | None = None
    low_ton: Decimal | None = None
    high_ton: Decimal | None = None
    range_percent: Decimal | None = None
    daily_percent: Decimal | None = None
    max_move_percent: Decimal | None = None
    max_drawdown_percent: Decimal | None = None
    confident: bool
    label: str


@router.get("/gifts/{gift_id}", response_model=GiftVolatility)
async def gift_volatility(
    gift_id: int,
    window_days: int = Query(default=14, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
):
    if await session.get(Gift, gift_id) is None:
        raise HTTPException(404, "Gift not found")
    stats = await VolatilityRepository(session).for_gift(gift_id, window_days=window_days)
    return GiftVolatility(**stats)
