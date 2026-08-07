from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.repositories import PriceHistoryRepository
from app.db.session import get_session

router = APIRouter(prefix="/history", tags=["history"])

@router.get("/gifts/{gift_id}")
async def gift_history(gift_id: int, marketplace: str | None = None, limit: int = Query(default=500, ge=1, le=5000), session: AsyncSession = Depends(get_session)):
    rows = await PriceHistoryRepository(session).history(gift_id=gift_id, marketplace=marketplace, limit=limit)
    return {
        "data_mode": "persisted",
        "gift_id": gift_id,
        "marketplace": marketplace,
        "points": [
            {"observed_at": row.observed_at, "marketplace": row.marketplace, "floor_ton": row.floor_ton, "median_ton": row.median_ton, "volume_ton": row.volume_ton, "listings_count": row.listings_count, "source_url": row.source_url}
            for row in rows
        ],
    }
