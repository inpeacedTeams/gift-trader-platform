from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import current_user
from app.db.models import Gift, PortfolioHolding, PortfolioValuation, PortfolioWallet, PriceSnapshot, User
from app.db.session import get_session
from app.market.models import SourceUnavailable
from app.portfolio.tonapi import TonapiPortfolioClient
from app.portfolio.valuation import latest_floor, resolve_gift

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.get("/overview")
async def portfolio_overview(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    wallets = list((await session.scalars(select(PortfolioWallet).where(PortfolioWallet.user_id == user.id).order_by(PortfolioWallet.created_at.desc()))).all()); client = TonapiPortfolioClient(); wallet_results = []; total_ton = Decimal("0"); total_assets = 0; valued_assets = 0; unavailable = []
    for wallet in wallets:
        try:
            account = await client.account(wallet.address); nft_items = await client.nft_items(wallet.address); holdings = []
            for item in nft_items:
                address = item.get("address")
                if not address: continue
                address = str(address); metadata = item.get("metadata") or {}; collection_address = str(item.get("collection", {}).get("address")) if isinstance(item.get("collection"), dict) and item.get("collection", {}).get("address") else None
                gift, source, confidence = await resolve_gift(session, nft_address=address, collection_address=collection_address, metadata=metadata); price = await latest_floor(session, gift)
                existing = await session.scalar(select(PortfolioHolding).where(PortfolioHolding.wallet_id == wallet.id, PortfolioHolding.nft_address == address))
                if existing is None: existing = PortfolioHolding(wallet_id=wallet.id, nft_address=address); session.add(existing)
                existing.collection_address = collection_address or existing.collection_address; existing.name = metadata.get("name") or existing.name; existing.image_url = metadata.get("image") or existing.image_url; existing.estimated_price_ton = price; existing.valuation_source = source; existing.valuation_confidence = confidence
                holdings.append({"nft_address": address, "name": metadata.get("name"), "image_url": metadata.get("image"), "estimated_price_ton": price, "valuation_source": source, "valuation_confidence": confidence})
                total_assets += 1
                if price is not None: total_ton += price; valued_assets += 1
            wallet_results.append({"wallet_id": wallet.id, "address": wallet.address, "label": wallet.label, "ton_balance": client.ton_balance(account), "nfts": holdings})
        except SourceUnavailable as exc: unavailable.append({"wallet_id": wallet.id, "address": wallet.address, "error": exc.reason})
    await session.commit(); return {"data_mode": "live-tonapi", "wallets": wallet_results, "total_assets": total_assets, "valued_assets": valued_assets, "unvalued_assets": total_assets - valued_assets, "estimated_nft_value_ton": total_ton, "unavailable": unavailable}

@router.get("/history")
async def portfolio_history(limit: int = Query(default=96, ge=1, le=1000), user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    rows = list((await session.scalars(select(PortfolioValuation).where(PortfolioValuation.user_id == user.id).order_by(PortfolioValuation.observed_at.desc()).limit(limit))).all()); rows.reverse()
    return {"data_mode": "persisted", "points": [{"observed_at": row.observed_at, "total_ton": row.total_ton, "ton_balance": row.ton_balance, "nft_value_ton": row.nft_value_ton, "asset_count": row.asset_count} for row in rows]}
