from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.movers import MoversRepository
from app.db.session import get_session
from app.schemas.frontend import MoverCard, MoversResponse

router = APIRouter(prefix="/movers", tags=["analytics"])


@router.get("", response_model=MoversResponse)
async def movers(
    hours: int = Query(default=24, ge=1, le=24 * 30),
    limit: int = Query(default=5, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
):
    result = await MoversRepository(session).movers(hours=hours, limit=limit)
    return MoversResponse(
        window_hours=hours,
        gainers=[MoverCard(**item) for item in result["gainers"]],
        losers=[MoverCard(**item) for item in result["losers"]],
    )
