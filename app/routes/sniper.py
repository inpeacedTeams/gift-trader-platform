from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user
from app.db.models import Gift, SniperHit, SniperWatch, User
from app.db.session import get_session

router = APIRouter(prefix="/sniper", tags=["sniper"])
MAX_WATCHES = 20


class WatchCreate(BaseModel):
    gift_name: str | None = Field(default=None, max_length=255)
    model: str | None = Field(default=None, max_length=255)
    max_price_ton: Decimal | None = Field(default=None, gt=0)
    min_discount_percent: Decimal | None = Field(default=None, ge=0, lt=100)
    marketplace: str | None = Field(default=None, max_length=64)

    def is_empty(self) -> bool:
        return not any(
            [self.gift_name, self.model, self.max_price_ton, self.min_discount_percent]
        )


class WatchCard(BaseModel):
    id: int
    gift_name: str | None = None
    model: str | None = None
    max_price_ton: Decimal | None = None
    min_discount_percent: Decimal | None = None
    marketplace: str | None = None
    is_active: bool
    hits: int = 0


class WatchList(BaseModel):
    items: list[WatchCard]


@router.get("/watches", response_model=WatchList)
async def watches(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    rows = list(
        (
            await session.scalars(
                select(SniperWatch)
                .where(SniperWatch.user_id == user.id)
                .order_by(SniperWatch.created_at.desc())
            )
        ).all()
    )
    counts = {}
    if rows:
        from sqlalchemy import func

        counts = dict(
            (
                await session.execute(
                    select(SniperHit.watch_id, func.count(SniperHit.id))
                    .where(SniperHit.watch_id.in_([row.id for row in rows]))
                    .group_by(SniperHit.watch_id)
                )
            ).all()
        )
    return WatchList(
        items=[
            WatchCard(
                id=row.id,
                gift_name=row.gift_name,
                model=row.model,
                max_price_ton=row.max_price_ton,
                min_discount_percent=row.min_discount_percent,
                marketplace=row.marketplace,
                is_active=row.is_active,
                hits=counts.get(row.id, 0),
            )
            for row in rows
        ]
    )


@router.post("/watches", response_model=WatchCard, status_code=201)
async def create_watch(
    body: WatchCreate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    """Standing order for the fast loop.

    An unfiltered watch would fire on every listing on the market, which is
    noise rather than a signal, so at least one condition is required.
    """
    if body.is_empty():
        raise HTTPException(422, "Задайте хотя бы одно условие: цену, скидку, название или модель")
    from sqlalchemy import func

    existing = await session.scalar(
        select(func.count(SniperWatch.id)).where(SniperWatch.user_id == user.id)
    )
    if (existing or 0) >= MAX_WATCHES:
        raise HTTPException(422, f"Максимум {MAX_WATCHES} правил снайпера")
    watch = SniperWatch(user_id=user.id, **body.model_dump())
    session.add(watch)
    await session.commit()
    await session.refresh(watch)
    return WatchCard(
        id=watch.id,
        gift_name=watch.gift_name,
        model=watch.model,
        max_price_ton=watch.max_price_ton,
        min_discount_percent=watch.min_discount_percent,
        marketplace=watch.marketplace,
        is_active=watch.is_active,
    )


@router.delete("/watches/{watch_id}", status_code=204)
async def delete_watch(
    watch_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        delete(SniperWatch).where(SniperWatch.id == watch_id, SniperWatch.user_id == user.id)
    )
    await session.commit()


@router.patch("/watches/{watch_id}", response_model=WatchCard)
async def toggle_watch(
    watch_id: int,
    is_active: bool,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    watch = await session.scalar(
        select(SniperWatch).where(SniperWatch.id == watch_id, SniperWatch.user_id == user.id)
    )
    if watch is None:
        raise HTTPException(404, "Правило не найдено")
    watch.is_active = is_active
    await session.commit()
    return WatchCard(
        id=watch.id,
        gift_name=watch.gift_name,
        model=watch.model,
        max_price_ton=watch.max_price_ton,
        min_discount_percent=watch.min_discount_percent,
        marketplace=watch.marketplace,
        is_active=watch.is_active,
    )


@router.get("/gifts/{gift_id}/liquidity")
async def gift_liquidity(gift_id: int, session: AsyncSession = Depends(get_session)):
    """How fast this gift turns over, and how solid its floor is."""
    from app.db.repositories.liquidity import LiquidityRepository, liquidity_label

    if await session.get(Gift, gift_id) is None:
        raise HTTPException(404, "Gift not found")
    repository = LiquidityRepository(session)
    stats = (await repository.for_gifts([gift_id])).get(gift_id, {})
    return {
        **stats,
        "label": liquidity_label(stats),
        "floor_gap_percent": await repository.floor_gap(gift_id),
    }
