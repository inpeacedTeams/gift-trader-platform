from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user
from app.db.models import Gift, Position, User
from app.db.repositories import PositionRepository
from app.db.session import get_session

router = APIRouter(prefix="/positions", tags=["positions"])
# Generous, but not unbounded: the P&L read prices every open lot at once.
MAX_OPEN_POSITIONS = 300


class PositionCreate(BaseModel):
    gift_id: int
    buy_price_ton: Decimal = Field(gt=0)
    buy_marketplace: str | None = Field(default=None, max_length=64)
    opened_at: datetime | None = None
    note: str | None = Field(default=None, max_length=255)


class PositionUpdate(BaseModel):
    """Close a lot, correct an entry, or put a closed one back on the book."""

    buy_price_ton: Decimal | None = Field(default=None, gt=0)
    buy_marketplace: str | None = Field(default=None, max_length=64)
    opened_at: datetime | None = None
    sell_price_ton: Decimal | None = Field(default=None, gt=0)
    sell_marketplace: str | None = Field(default=None, max_length=64)
    closed_at: datetime | None = None
    note: str | None = Field(default=None, max_length=255)
    reopen: bool = False


class PositionCard(BaseModel):
    id: int
    gift_id: int
    name: str | None = None
    model: str | None = None
    gift_number: int | None = None
    image_url: str | None = None
    rarity_tier: str | None = None
    collection_name: str | None = None
    buy_price_ton: Decimal
    buy_marketplace: str | None = None
    opened_at: datetime
    sell_price_ton: Decimal | None = None
    sell_marketplace: str | None = None
    closed_at: datetime | None = None
    note: str | None = None
    is_open: bool
    days_held: int
    cost_ton: Decimal
    gas_ton: Decimal
    exit_marketplace: str | None = None
    exit_fee_percent: Decimal
    floor_ton: Decimal | None = None
    net_value_ton: Decimal | None = None
    profit_ton: Decimal | None = None
    profit_percent: Decimal | None = None
    # False when nothing is listed, so the row says "no price" instead of
    # quoting one we do not have.
    valued: bool


class PositionSummary(BaseModel):
    open_count: int
    closed_count: int
    unvalued_count: int
    invested_ton: Decimal
    market_value_ton: Decimal
    unrealized_ton: Decimal
    unrealized_percent: Decimal | None = None
    realized_ton: Decimal
    win_rate_percent: Decimal | None = None


class PositionList(BaseModel):
    data_mode: str = "live-only"
    items: list[PositionCard]
    summary: PositionSummary


async def _owned(position_id: int, user: User, session: AsyncSession) -> Position:
    position = await session.scalar(
        select(Position).where(Position.id == position_id, Position.user_id == user.id)
    )
    if position is None:
        raise HTTPException(404, "Позиция не найдена")
    return position


@router.get("", response_model=PositionList)
async def positions(
    include_closed: bool = Query(default=True),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    """Every lot with its P&L, priced at what an exit would really pay."""
    result = await PositionRepository(session).list(user.id, include_closed=include_closed)
    return PositionList(
        items=[PositionCard(**item) for item in result["items"]],
        summary=PositionSummary(**result["summary"]),
    )


@router.post("", response_model=PositionCard, status_code=201)
async def create_position(
    body: PositionCreate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    if await session.get(Gift, body.gift_id) is None:
        raise HTTPException(404, "Подарок не найден")
    open_lots = await session.scalar(
        select(func.count(Position.id)).where(
            Position.user_id == user.id, Position.closed_at.is_(None)
        )
    )
    if (open_lots or 0) >= MAX_OPEN_POSITIONS:
        raise HTTPException(422, f"Максимум {MAX_OPEN_POSITIONS} открытых позиций")
    position = Position(
        user_id=user.id,
        gift_id=body.gift_id,
        buy_price_ton=body.buy_price_ton,
        buy_marketplace=body.buy_marketplace,
        opened_at=body.opened_at or datetime.now(timezone.utc),
        note=body.note,
    )
    session.add(position)
    await session.commit()
    await session.refresh(position)
    return PositionCard(**await PositionRepository(session).card(position))


@router.patch("/{position_id}", response_model=PositionCard)
async def update_position(
    position_id: int,
    body: PositionUpdate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    position = await _owned(position_id, user, session)
    if body.buy_price_ton is not None:
        position.buy_price_ton = body.buy_price_ton
    if body.buy_marketplace is not None:
        position.buy_marketplace = body.buy_marketplace
    if body.opened_at is not None:
        position.opened_at = body.opened_at
    if body.note is not None:
        position.note = body.note
    if body.reopen:
        # Sold by mistake, or the sale fell through. The entry survives.
        position.sell_price_ton = None
        position.sell_marketplace = None
        position.closed_at = None
    else:
        if body.sell_marketplace is not None:
            position.sell_marketplace = body.sell_marketplace
        if body.sell_price_ton is not None:
            position.sell_price_ton = body.sell_price_ton
            position.closed_at = body.closed_at or position.closed_at or datetime.now(timezone.utc)
        elif body.closed_at is not None:
            position.closed_at = body.closed_at
    if position.closed_at is not None and position.sell_price_ton is None:
        raise HTTPException(422, "Укажите цену продажи, чтобы закрыть позицию")
    await session.commit()
    await session.refresh(position)
    return PositionCard(**await PositionRepository(session).card(position))


@router.delete("/{position_id}", status_code=204)
async def delete_position(
    position_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        delete(Position).where(Position.id == position_id, Position.user_id == user.id)
    )
    await session.commit()
