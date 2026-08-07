from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import delete, select
from app.db.models import Gift, PortfolioHolding, PortfolioWallet, PriceSnapshot
from app.db.session import SessionLocal
from app.market.models import SourceUnavailable
from app.portfolio.tonapi import TonapiPortfolioClient

@dataclass(frozen=True)
class PortfolioSyncReport:
    wallets: int
    synced_wallets: int
    holdings: int
    unavailable: int

async def sync_portfolios() -> PortfolioSyncReport:
    client = TonapiPortfolioClient()
    async with SessionLocal() as session:
        wallets = list((await session.scalars(select(PortfolioWallet))).all())
        synced_wallets = 0
        holdings_count = 0
        unavailable = 0
        for wallet in wallets:
            try:
                nft_items = await client.nft_items(wallet.address)
                seen: list[str] = []
                for item in nft_items:
                    address = item.get("address")
                    if not address:
                        continue
                    address = str(address)
                    seen.append(address)
                    metadata = item.get("metadata") or {}
                    gift = await session.scalar(select(Gift).where(Gift.canonical_id == address))
                    price = None
                    if gift:
                        snapshot = await session.scalar(select(PriceSnapshot).where(PriceSnapshot.gift_id == gift.id).order_by(PriceSnapshot.observed_at.desc()).limit(1))
                        price = snapshot.floor_ton if snapshot else None
                    holding = await session.scalar(select(PortfolioHolding).where(PortfolioHolding.wallet_id == wallet.id, PortfolioHolding.nft_address == address))
                    if holding is None:
                        holding = PortfolioHolding(wallet_id=wallet.id, nft_address=address)
                        session.add(holding)
                    holding.collection_address = str(item.get("collection", {}).get("address")) if isinstance(item.get("collection"), dict) else holding.collection_address
                    holding.name = metadata.get("name") or holding.name
                    holding.image_url = metadata.get("image") or holding.image_url
                    holding.estimated_price_ton = price
                    holding.observed_at = datetime.now(timezone.utc)
                    holdings_count += 1
                if seen:
                    await session.execute(delete(PortfolioHolding).where(PortfolioHolding.wallet_id == wallet.id, PortfolioHolding.nft_address.not_in(seen)))
                else:
                    await session.execute(delete(PortfolioHolding).where(PortfolioHolding.wallet_id == wallet.id))
                synced_wallets += 1
            except SourceUnavailable:
                unavailable += 1
        await session.commit()
    return PortfolioSyncReport(len(wallets), synced_wallets, holdings_count, unavailable)
