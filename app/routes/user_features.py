from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import current_user
from app.db.models import AlertEvent, AlertRule, Collection, Gift, PortfolioWallet, User, WatchlistItem
from app.db.repositories import WatchlistRepository
from app.db.session import get_session
from app.schemas.frontend import WatchlistCard, WatchlistPage

router = APIRouter(tags=["user-features"])


class WalletCreate(BaseModel):
    address: str = Field(min_length=10, max_length=128)
    label: str | None = Field(default=None, max_length=255)


class AlertCreate(BaseModel):
    gift_id: int | None = None
    rule_type: str = Field(pattern="^(price_below|price_above|change_percent|listed_below|portfolio_value_above|portfolio_value_below|portfolio_change_percent)$")
    threshold: Decimal = Field(gt=0)


class AlertUpdate(BaseModel):
    is_active: bool


async def _gift_exists(session: AsyncSession, gift_id: int) -> bool:
    return await session.scalar(select(Gift.id).where(Gift.id == gift_id)) is not None


async def _gift_labels(session: AsyncSession, gift_ids: set[int]) -> dict[int, dict]:
    """Name, model and image for every gift referenced by a rule or event.

    Resolved in one query so a page of alerts does not fan out into a
    lookup per row.
    """
    ids = {gift_id for gift_id in gift_ids if gift_id}
    if not ids:
        return {}
    rows = (
        await session.execute(
            select(Gift.id, Gift.name, Gift.model, Gift.image_url, Collection.name.label("collection"))
            .outerjoin(Collection, Collection.id == Gift.collection_id)
            .where(Gift.id.in_(ids))
        )
    ).all()
    return {
        row.id: {
            "gift_name": row.name or row.collection,
            "gift_model": row.model,
            "gift_image_url": row.image_url,
        }
        for row in rows
    }


@router.get("/watchlist", response_model=WatchlistPage)
async def watchlist(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    """Saved gifts as full cards, priced from the live book."""
    repository = WatchlistRepository(session)
    rows = await repository.cards(user.id)
    venues = await repository.best_venues([row["id"] for row in rows])
    return WatchlistPage(
        items=[WatchlistCard(**row, best_marketplace=venues.get(row["id"])) for row in rows]
    )


@router.post("/watchlist/{gift_id}", status_code=201)
async def add_watchlist(gift_id: int, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    if not await _gift_exists(session, gift_id): raise HTTPException(404, "Gift not found")
    item = await session.scalar(select(WatchlistItem).where(WatchlistItem.user_id == user.id, WatchlistItem.gift_id == gift_id))
    if item is None: item = WatchlistItem(user_id=user.id, gift_id=gift_id); session.add(item); await session.commit(); await session.refresh(item)
    return {"id": item.id, "gift_id": item.gift_id, "created_at": item.created_at}


@router.delete("/watchlist/{gift_id}", status_code=204)
async def remove_watchlist(gift_id: int, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    await session.execute(delete(WatchlistItem).where(WatchlistItem.user_id == user.id, WatchlistItem.gift_id == gift_id)); await session.commit()


@router.get("/portfolio/wallets")
async def wallets(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(PortfolioWallet).where(PortfolioWallet.user_id == user.id).order_by(PortfolioWallet.created_at.desc()))).all(); return {"items": [{"id": row.id, "address": row.address, "label": row.label, "created_at": row.created_at} for row in rows]}


@router.post("/portfolio/wallets", status_code=201)
async def add_wallet(body: WalletCreate, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    wallet = await session.scalar(select(PortfolioWallet).where(PortfolioWallet.user_id == user.id, PortfolioWallet.address == body.address))
    if wallet is None: wallet = PortfolioWallet(user_id=user.id, address=body.address, label=body.label); session.add(wallet); await session.commit(); await session.refresh(wallet)
    return {"id": wallet.id, "address": wallet.address, "label": wallet.label, "created_at": wallet.created_at}


@router.delete("/portfolio/wallets/{wallet_id}", status_code=204)
async def remove_wallet(wallet_id: int, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    await session.execute(delete(PortfolioWallet).where(PortfolioWallet.id == wallet_id, PortfolioWallet.user_id == user.id)); await session.commit()


@router.get("/alerts/rules")
async def alert_rules(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    rows = (
        await session.scalars(
            select(AlertRule).where(AlertRule.user_id == user.id).order_by(AlertRule.created_at.desc())
        )
    ).all()
    labels = await _gift_labels(session, {row.gift_id for row in rows if row.gift_id})
    return {
        "items": [
            {
                "id": row.id,
                "gift_id": row.gift_id,
                "rule_type": row.rule_type,
                "threshold": row.threshold,
                "is_active": row.is_active,
                "created_at": row.created_at,
                **labels.get(row.gift_id or 0, {}),
            }
            for row in rows
        ]
    }


@router.post("/alerts/rules", status_code=201)
async def create_alert(body: AlertCreate, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    if body.gift_id is not None and body.rule_type.startswith("portfolio_"): raise HTTPException(422, "Portfolio alerts cannot target a gift")
    if body.gift_id is not None and not await _gift_exists(session, body.gift_id): raise HTTPException(404, "Gift not found")
    rule = AlertRule(user_id=user.id, gift_id=body.gift_id, rule_type=body.rule_type, threshold=body.threshold)
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    labels = await _gift_labels(session, {rule.gift_id} if rule.gift_id else set())
    return {
        "id": rule.id,
        "gift_id": rule.gift_id,
        "rule_type": rule.rule_type,
        "threshold": rule.threshold,
        "is_active": rule.is_active,
        **labels.get(rule.gift_id or 0, {}),
    }


@router.patch("/alerts/rules/{rule_id}")
async def update_alert(rule_id: int, body: AlertUpdate, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    rule = await session.scalar(select(AlertRule).where(AlertRule.id == rule_id, AlertRule.user_id == user.id))
    if rule is None: raise HTTPException(404, "Alert rule not found")
    rule.is_active = body.is_active; await session.commit(); return {"id": rule.id, "is_active": rule.is_active}


@router.delete("/alerts/rules/{rule_id}", status_code=204)
async def delete_alert(rule_id: int, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    await session.execute(delete(AlertRule).where(AlertRule.id == rule_id, AlertRule.user_id == user.id)); await session.commit()


@router.get("/alerts/events")
async def alert_events(unread_only: bool = False, limit: int = Query(default=50, ge=1, le=200), user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    stmt = select(AlertEvent).where(AlertEvent.user_id == user.id)
    if unread_only: stmt = stmt.where(AlertEvent.is_read.is_(False))
    rows = (await session.scalars(stmt.order_by(AlertEvent.created_at.desc()).limit(limit))).all()
    labels = await _gift_labels(session, {row.gift_id for row in rows if row.gift_id})
    return {
        "items": [
            {
                "id": row.id,
                "rule_id": row.rule_id,
                "gift_id": row.gift_id,
                "message": row.message,
                "observed_value": row.observed_value,
                "is_read": row.is_read,
                "created_at": row.created_at,
                **labels.get(row.gift_id or 0, {}),
            }
            for row in rows
        ]
    }


@router.patch("/alerts/events/{event_id}/read")
async def mark_alert_read(event_id: int, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    event = await session.scalar(select(AlertEvent).where(AlertEvent.id == event_id, AlertEvent.user_id == user.id))
    if event is None: raise HTTPException(404, "Alert event not found")
    event.is_read = True; await session.commit(); return {"id": event.id, "is_read": event.is_read}
