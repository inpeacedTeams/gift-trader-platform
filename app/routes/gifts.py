from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Gift, PriceSnapshot
from app.db.repositories import GiftRepository, PriceHistoryRepository
from app.db.session import get_session
from app.schemas.frontend import GiftCard, GiftDetail, GiftHistory, GiftListing, GiftPage, PricePoint

router = APIRouter(prefix="/gifts", tags=["gifts"])

@router.get("", response_model=GiftPage)
async def gifts(page: int = Query(default=1, ge=1), page_size: int = Query(default=24, ge=1, le=100), search: str | None = None, marketplace: str | None = None, session: AsyncSession = Depends(get_session)):
    rows, total = await GiftRepository(session).page(page=page, page_size=page_size, search=search, marketplace=marketplace)
    items = []
    for gift in rows:
        point = await session.scalar(select(PriceSnapshot).where(PriceSnapshot.gift_id == gift.id).order_by(PriceSnapshot.observed_at.desc()).limit(1))
        items.append(GiftCard(id=gift.id, canonical_id=gift.canonical_id, name=gift.name, model=gift.model, gift_number=gift.gift_number, image_url=gift.image_url, floor_ton=point.floor_ton if point else None, median_ton=point.median_ton if point else None, listings_count=point.listings_count if point else 0))
    return GiftPage(items=items, page=page, page_size=page_size, total=total, has_next=page * page_size < total)

@router.get("/{gift_id}", response_model=GiftDetail)
async def gift_detail(gift_id: int, session: AsyncSession = Depends(get_session)):
    result = await GiftRepository(session).detail(gift_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Gift not found")
    gift, listings = result
    point = (await GiftRepository(session).latest_stats(gift_id) or [None])[0]
    return GiftDetail(id=gift.id, canonical_id=gift.canonical_id, name=gift.name, model=gift.model, gift_number=gift.gift_number, image_url=gift.image_url, floor_ton=point.floor_ton if point else None, median_ton=point.median_ton if point else None, listings_count=point.listings_count if point else 0, listings=[GiftListing.model_validate(item) for item in listings], sources=sorted({item.marketplace for item in listings}))

@router.get("/{gift_id}/history", response_model=GiftHistory)
async def gift_history(gift_id: int, marketplace: str | None = None, limit: int = Query(default=500, ge=1, le=5000), session: AsyncSession = Depends(get_session)):
    if await session.get(Gift, gift_id) is None:
        raise HTTPException(status_code=404, detail="Gift not found")
    rows = await PriceHistoryRepository(session).history(gift_id=gift_id, marketplace=marketplace, limit=limit)
    return GiftHistory(gift_id=gift_id, points=[PricePoint.model_validate(row) for row in rows])
