from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Gift
from app.db.repositories import GiftRepository, PriceHistoryRepository, TradeRepository
from app.db.repositories.gifts import SORTS
from app.db.session import get_session
from app.schemas.frontend import (
    GiftCard,
    GiftDetail,
    GiftHistory,
    GiftListing,
    GiftPage,
    GiftTrades,
    PricePoint,
    TradeRecord,
    TradeStats,
)

router = APIRouter(prefix="/gifts", tags=["gifts"])


@router.get("", response_model=GiftPage)
async def gifts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    search: str | None = None,
    marketplace: str | None = None,
    collection_id: int | None = Query(default=None, ge=1),
    model: str | None = None,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    deals_only: bool = Query(default=False),
    sort: str = Query(default="recent", pattern=f"^({'|'.join(SORTS)})$"),
    session: AsyncSession = Depends(get_session),
):
    repository = GiftRepository(session)
    rows, total, changes, venues = await repository.page(
        page=page,
        page_size=page_size,
        search=search,
        marketplace=marketplace,
        collection_id=collection_id,
        model=model,
        min_price=min_price,
        max_price=max_price,
        deals_only=deals_only,
        sort=sort,
    )
    names: dict[int, str | None] = {}
    items = []
    for gift, floor_ton, median_ton, listings_count, deal_percent in rows:
        if gift.collection_id is not None and gift.collection_id not in names:
            names[gift.collection_id] = await repository.collection_name(gift.collection_id)
        items.append(
            GiftCard(
                id=gift.id,
                canonical_id=gift.canonical_id,
                collection_id=gift.collection_id,
                collection_name=names.get(gift.collection_id) if gift.collection_id else None,
                name=gift.name,
                model=gift.model,
                gift_number=gift.gift_number,
                image_url=gift.image_url,
                floor_ton=floor_ton,
                median_ton=median_ton,
                listings_count=listings_count,
                change_percent=changes.get(gift.id),
                best_marketplace=venues.get(gift.id),
                deal_percent=deal_percent,
            )
        )
    return GiftPage(items=items, page=page, page_size=page_size, total=total, has_next=page * page_size < total)


@router.get("/models", response_model=list[str])
async def gift_models(
    collection_id: int | None = Query(default=None, ge=1),
    session: AsyncSession = Depends(get_session),
):
    return await GiftRepository(session).models(collection_id)


@router.get("/{gift_id}", response_model=GiftDetail)
async def gift_detail(gift_id: int, session: AsyncSession = Depends(get_session)):
    repository = GiftRepository(session)
    result = await repository.detail(gift_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Gift not found")
    gift, listings = result
    active = sorted([item for item in listings if item.active], key=lambda item: item.price_ton)
    prices = [item.price_ton for item in active]
    floor = prices[0] if prices else None
    changes = await repository.changes([gift_id])
    return GiftDetail(
        id=gift.id,
        canonical_id=gift.canonical_id,
        collection_id=gift.collection_id,
        collection_name=await repository.collection_name(gift.collection_id),
        name=gift.name,
        model=gift.model,
        gift_number=gift.gift_number,
        image_url=gift.image_url,
        floor_ton=floor,
        median_ton=prices[len(prices) // 2] if prices else None,
        listings_count=len(active),
        change_percent=changes.get(gift_id),
        best_marketplace=active[0].marketplace if active else None,
        deal_percent=await repository.deal_percent(gift, floor),
        listings=[GiftListing.model_validate(item) for item in listings],
        sources=sorted({item.marketplace for item in active}),
    )


@router.get("/{gift_id}/trades", response_model=GiftTrades)
async def gift_trades(
    gift_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    window_days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
):
    """Prices the market actually paid, as opposed to asking prices."""
    if await session.get(Gift, gift_id) is None:
        raise HTTPException(status_code=404, detail="Gift not found")
    repository = TradeRepository(session)
    rows = await repository.recent(gift_id, limit=limit)
    stats = await repository.stats(gift_id, days=window_days)
    return GiftTrades(
        gift_id=gift_id,
        stats=TradeStats(**stats),
        items=[TradeRecord.model_validate(row) for row in rows],
    )


@router.get("/{gift_id}/history", response_model=GiftHistory)
async def gift_history(
    gift_id: int,
    marketplace: str | None = None,
    limit: int = Query(default=500, ge=1, le=5000),
    session: AsyncSession = Depends(get_session),
):
    if await session.get(Gift, gift_id) is None:
        raise HTTPException(status_code=404, detail="Gift not found")
    rows = await PriceHistoryRepository(session).history(gift_id=gift_id, marketplace=marketplace, limit=limit)
    return GiftHistory(gift_id=gift_id, points=[PricePoint.model_validate(row) for row in rows])
