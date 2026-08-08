from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.deals import DealRepository
from app.db.session import get_session
from app.schemas.frontend import Deal, DealList

router = APIRouter(prefix="/deals", tags=["deals"])


@router.get("", response_model=DealList)
async def deals(
    min_discount_percent: Decimal = Query(default=Decimal(10), ge=0, le=99),
    collection_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """Active listings priced below the median of their own model."""
    rows = await DealRepository(session).deals(
        min_discount_percent=min_discount_percent,
        collection_id=collection_id,
        limit=limit,
    )
    return DealList(items=[Deal(**row) for row in rows])
