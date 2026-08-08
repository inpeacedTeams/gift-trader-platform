from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user
from app.db.models import SellerIdentity, User
from app.db.repositories import SellingRepository
from app.db.session import get_session

router = APIRouter(prefix="/selling", tags=["selling"])
MAX_IDENTITIES = 10


class IdentityCreate(BaseModel):
    seller: str = Field(min_length=1, max_length=255)
    # None means the handle counts on every venue.
    marketplace: str | None = Field(default=None, max_length=64)


class IdentityCard(BaseModel):
    id: int
    seller: str
    marketplace: str | None = None
    source: str
    created_at: datetime


class IdentityList(BaseModel):
    items: list[IdentityCard]


class MyListing(BaseModel):
    listing_id: int
    gift_id: int
    name: str | None = None
    model: str | None = None
    backdrop: str | None = None
    symbol: str | None = None
    rarity_tier: str | None = None
    gift_number: int | None = None
    image_url: str | None = None
    collection_name: str | None = None
    marketplace: str
    price_ton: Decimal
    net_proceeds_ton: Decimal
    url: str | None = None
    listed_at: datetime
    rival_price_ton: Decimal | None = None
    rival_marketplace: str | None = None
    rival_url: str | None = None
    rival_gift_id: int | None = None
    competitors: int = 0
    undercut: bool
    undercut_percent: Decimal | None = None


class SellingSummary(BaseModel):
    listed_count: int
    undercut_count: int
    listed_value_ton: Decimal
    net_value_ton: Decimal


class SellingPage(BaseModel):
    data_mode: str = "live-only"
    items: list[MyListing]
    summary: SellingSummary
    identities: list[IdentityCard]


async def _register_telegram_identity(session: AsyncSession, user: User) -> None:
    """The signed in Telegram id is the seller id on Tonnel and MRKT.

    Recorded on read as well as on login so accounts created before this
    existed pick it up the first time they open the page.
    """
    handle = str(user.telegram_id)
    existing = await session.scalar(
        select(SellerIdentity.id).where(
            SellerIdentity.user_id == user.id,
            SellerIdentity.seller == handle,
            SellerIdentity.marketplace.is_(None),
        )
    )
    if existing is None:
        session.add(
            SellerIdentity(
                user_id=user.id, seller=handle, marketplace=None, source="telegram"
            )
        )
        await session.commit()


@router.get("/listings", response_model=SellingPage)
async def my_listings(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    """Lots on sale under this account, and who is standing in front of them."""
    await _register_telegram_identity(session, user)
    repository = SellingRepository(session)
    result = await repository.my_listings(user.id)
    identities = await repository.identities(user.id)
    return SellingPage(
        items=[MyListing(**item) for item in result["items"]],
        summary=SellingSummary(**result["summary"]),
        identities=[IdentityCard.model_validate(item, from_attributes=True) for item in identities],
    )


@router.get("/identities", response_model=IdentityList)
async def identities(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    rows = await SellingRepository(session).identities(user.id)
    return IdentityList(
        items=[IdentityCard.model_validate(row, from_attributes=True) for row in rows]
    )


@router.post("/identities", response_model=IdentityCard, status_code=201)
async def add_identity(
    body: IdentityCreate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    """Claim a seller handle on a venue that does not publish a Telegram id.

    Unverified by nature: we can only take the user's word for it, which is
    why the source is recorded and shown next to the handle.
    """
    count = await session.scalar(
        select(func.count(SellerIdentity.id)).where(SellerIdentity.user_id == user.id)
    )
    if (count or 0) >= MAX_IDENTITIES:
        raise HTTPException(422, f"Максимум {MAX_IDENTITIES} продавцов")
    handle = body.seller.strip()
    marketplace = body.marketplace.strip().lower() if body.marketplace else None
    duplicate = await session.scalar(
        select(SellerIdentity.id).where(
            SellerIdentity.user_id == user.id,
            SellerIdentity.seller == handle,
            SellerIdentity.marketplace.is_(marketplace)
            if marketplace is None
            else SellerIdentity.marketplace == marketplace,
        )
    )
    if duplicate is not None:
        raise HTTPException(422, "Этот продавец уже добавлен")
    identity = SellerIdentity(
        user_id=user.id, seller=handle, marketplace=marketplace, source="manual"
    )
    session.add(identity)
    await session.commit()
    await session.refresh(identity)
    return IdentityCard.model_validate(identity, from_attributes=True)


@router.delete("/identities/{identity_id}", status_code=204)
async def remove_identity(
    identity_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        delete(SellerIdentity).where(
            SellerIdentity.id == identity_id, SellerIdentity.user_id == user.id
        )
    )
    await session.commit()
