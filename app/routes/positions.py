from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user
from app.db.base import utc_now
from app.db.models import Gift, Position, User
from app.db.repositories import PositionRepository
from app.db.session import get_session
from app.schemas.positions import (
    PositionCard,
    PositionCreate,
    PositionList,
    PositionSummary,
    PositionUpdate,
)

router = APIRouter(prefix="/positions", tags=["positions"])


async def _card(session: AsyncSession, user_id: int, position_id: int) -> PositionCard:
    """Reload through the repository so a write answers with live pricing."""
    cards = await PositionRepository(session).cards(user_id)
    for card in cards:
        if card["id"] == position_id:
            return PositionCard(**card)
    raise HTTPException(404, "Position not found")


@router.get("", response_model=PositionList)
async def list_positions(
    include_closed: bool = True,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    repository = PositionRepository(session)
    cards = await repository.cards(user.id, include_closed=include_closed)
    return PositionList(
        items=[PositionCard(**card) for card in cards],
        summary=PositionSummary(**repository.summary(cards)),
    )


@router.post("", response_model=PositionCard, status_code=201)
async def open_position(
    body: PositionCreate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    if await session.scalar(select(Gift.id).where(Gift.id == body.gift_id)) is None:
        raise HTTPException(404, "Gift not found")
    position = Position(
        user_id=user.id,
        gift_id=body.gift_id,
        buy_price_ton=body.buy_price_ton,
        marketplace=body.marketplace,
        quantity=body.quantity,
        note=body.note,
    )
    if body.opened_at is not None:
        position.opened_at = body.opened_at
    session.add(position)
    await session.commit()
    await session.refresh(position)
    return await _card(session, user.id, position.id)


@router.patch("/{position_id}", response_model=PositionCard)
async def update_position(
    position_id: int,
    body: PositionUpdate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    position = await session.scalar(
        select(Position).where(Position.id == position_id, Position.user_id == user.id)
    )
    if position is None:
        raise HTTPException(404, "Position not found")

    sent = body.model_fields_set
    for field in ("buy_price_ton", "quantity", "marketplace", "sell_marketplace", "note"):
        if field in sent:
            setattr(position, field, getattr(body, field))
    if "sell_price_ton" in sent:
        position.sell_price_ton = body.sell_price_ton
        if body.sell_price_ton is None:
            # Undoing an exit: the position goes back on the open book.
            position.closed_at = None
            position.sell_marketplace = None
        elif position.closed_at is None:
            position.closed_at = utc_now()
    if "closed_at" in sent and body.closed_at is not None:
        if position.sell_price_ton is None:
            raise HTTPException(422, "Closing a position needs a sale price")
        position.closed_at = body.closed_at

    await session.commit()
    return await _card(session, user.id, position.id)


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
