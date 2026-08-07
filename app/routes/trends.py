from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.market.trends import price_trend

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/gifts/{gift_id}/trend")
async def gift_trend(gift_id: int, marketplace: str | None = None, window_hours: int = Query(default=24, ge=1, le=24 * 30), session: AsyncSession = Depends(get_session)):
    return {"data_mode": "persisted", "gift_id": gift_id, **(await price_trend(session, gift_id=gift_id, marketplace=marketplace, window_hours=window_hours))}
