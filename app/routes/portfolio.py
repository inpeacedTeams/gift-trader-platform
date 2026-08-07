from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import current_user
from app.db.models import Gift, PortfolioHolding, PortfolioValuation, PortfolioWallet, PriceSnapshot, User
from app.db.session import get_session
from app.market.models import SourceUnavailable
from app.portfolio.tonapi import TonapiPortfolioClient

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.get("/overview")
async def portfolio_overview(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    wallets = list((await session.scalars(select(PortfolioWallet).where(PortfolioWallet.user_id == user.id).order_by(PortfolioWallet.created_at.desc()))).all())
    client = TonapiPortfolioClient(); wallet_results = []; total_ton = Decimal("0"); total_assets = 0; unavailable = []
    for wallet in wallets:
        try:
            account = await client.account(wallet.address); nft_items = await client.nft_items(wallet.address); holdings = []
            for item in nft_items:
                address = item.get("address")
                if not address: continue
                metadata = item.get("metadata") or {}; gift = await session.scalar(select(Gift).where(Gift.canonical_id == str(address))); price = None
                if gift:
                    snapshot = await session.scalar(select(PriceSnapshot).where(PriceSnapshot.gift_id == gift.id).order_by(PriceSnapshot.observed_at.desc()).limit(1)); price = snapshot.floor_ton if snapshot else None
                existing = await session.scalar(select(PortfolioHolding).where(PortfolioHolding.wallet_id == wallet.id, PortfolioHolding.nft_address == str(address)))
                if existing is None: existing = PortfolioHolding(wallet_id=wallet.id, nft_address=str(address), collection_address=str(item.get("collection", {}).get("address")) if isinstance(item.get("collection"), dict) else None, name=metadata.get("name"), image_url=metadata.get("image"), estimated_price_ton=price); session.add(existing)
                else: existing.name = metadata.get("name") or existing.name; existing.image_url = metadata.get("image") or existing.image_url; existing.estimated_price_ton = price
                holdings.append({"nft_address": address, "name": metadata.get("name"), "image_url": metadata.get("image"), "estimated_price_ton": price})
                if price is not None: total_ton += price
            total_assets += len(holdings); wallet_results.append({"wallet_id": wallet.id, "address": wallet.address, "label": wallet.label, "ton_balance": client.ton_balance(account), "nfts": holdings})
        except SourceUnavailable as exc: unavailable.append({"wallet_id": wallet.id, "address": wallet.address, "error": exc.reason})
    await session.commit(); return {"data_mode": "live-tonapi", "wallets": wallet_results, "total_assets": total_assets, "estimated_nft_value_ton": total_ton, "unavailable": unavailable}

@router.get("/history")
async def portfolio_history(limit: int = Query(default=96, ge=1, le=1000), user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    rows = list((await session.scalars(select(PortfolioValuation).where(PortfolioValuation.user_id == user.id).order_by(PortfolioValuation.observed_at.desc()).limit(limit))).all())
    rows.reverse()
    return {"data_mode": "persisted", "points": [{"observed_at": row.observed_at, "total_ton": row.total_ton, "ton_balance": row.ton_balance, "nft_value_ton": row.nft_value_ton, "asset_count": row.asset_count} for row in rows]}
