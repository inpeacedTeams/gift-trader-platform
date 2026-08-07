from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import delete, select
from app.db.models import AlertEvent, AlertRule, Gift, PortfolioHolding, PortfolioValuation, PortfolioWallet, PriceSnapshot
from app.db.session import SessionLocal
from app.market.models import SourceUnavailable
from app.portfolio.tonapi import TonapiPortfolioClient

@dataclass(frozen=True)
class PortfolioSyncReport:
    wallets: int
    synced_wallets: int
    holdings: int
    unavailable: int
    alerts: int = 0

async def sync_portfolios() -> PortfolioSyncReport:
    client = TonapiPortfolioClient()
    async with SessionLocal() as session:
        wallets = list((await session.scalars(select(PortfolioWallet))).all()); synced_wallets = holdings_count = unavailable = alerts_count = 0
        for wallet in wallets:
            try:
                nft_items = await client.nft_items(wallet.address); seen: list[str] = []
                for item in nft_items:
                    address = item.get("address")
                    if not address: continue
                    address = str(address); seen.append(address); metadata = item.get("metadata") or {}
                    gift = await session.scalar(select(Gift).where(Gift.canonical_id == address)); price = None
                    if gift:
                        snapshot = await session.scalar(select(PriceSnapshot).where(PriceSnapshot.gift_id == gift.id).order_by(PriceSnapshot.observed_at.desc()).limit(1)); price = snapshot.floor_ton if snapshot else None
                    holding = await session.scalar(select(PortfolioHolding).where(PortfolioHolding.wallet_id == wallet.id, PortfolioHolding.nft_address == address))
                    if holding is None: holding = PortfolioHolding(wallet_id=wallet.id, nft_address=address); session.add(holding)
                    holding.collection_address = str(item.get("collection", {}).get("address")) if isinstance(item.get("collection"), dict) else holding.collection_address; holding.name = metadata.get("name") or holding.name; holding.image_url = metadata.get("image") or holding.image_url; holding.estimated_price_ton = price; holding.observed_at = datetime.now(timezone.utc); holdings_count += 1
                if seen: await session.execute(delete(PortfolioHolding).where(PortfolioHolding.wallet_id == wallet.id, PortfolioHolding.nft_address.not_in(seen)))
                else: await session.execute(delete(PortfolioHolding).where(PortfolioHolding.wallet_id == wallet.id))
                synced_wallets += 1
            except SourceUnavailable: unavailable += 1
        user_ids = {wallet.user_id for wallet in wallets}
        for user_id in user_ids:
            valuation = await _record_user_valuation(session, user_id, wallets, client); alerts_count += await _evaluate_alerts(session, user_id, valuation)
        await session.commit()
    return PortfolioSyncReport(len(wallets), synced_wallets, holdings_count, unavailable, alerts_count)

async def _record_user_valuation(session, user_id, wallets, client):
    user_wallets = [wallet for wallet in wallets if wallet.user_id == user_id]; wallet_ids = [wallet.id for wallet in user_wallets]
    holdings = list((await session.scalars(select(PortfolioHolding).where(PortfolioHolding.wallet_id.in_(wallet_ids)))).all()) if wallet_ids else []
    nft_value = sum((item.estimated_price_ton or Decimal("0") for item in holdings), Decimal("0")); ton_balance = Decimal("0")
    for wallet in user_wallets:
        try: ton_balance += client.ton_balance(await client.account(wallet.address))
        except SourceUnavailable: pass
    valuation = PortfolioValuation(user_id=user_id, total_ton=ton_balance + nft_value, ton_balance=ton_balance, nft_value_ton=nft_value, asset_count=len(holdings), observed_at=datetime.now(timezone.utc)); session.add(valuation); await session.flush(); return valuation

async def _evaluate_alerts(session, user_id, current: PortfolioValuation) -> int:
    previous = await session.scalar(select(PortfolioValuation).where(PortfolioValuation.user_id == user_id, PortfolioValuation.id < current.id).order_by(PortfolioValuation.id.desc()).limit(1))
    if previous is None: return 0
    rules = list((await session.scalars(select(AlertRule).where(AlertRule.user_id == user_id, AlertRule.is_active.is_(True), AlertRule.gift_id.is_(None), AlertRule.rule_type.in_(["portfolio_value_above", "portfolio_value_below", "portfolio_change_percent"]))).all())
    change = ((current.total_ton - previous.total_ton) / previous.total_ton * Decimal("100")) if previous.total_ton else Decimal("0"); count = 0
    for rule in rules:
        triggered = (rule.rule_type == "portfolio_value_above" and current.total_ton >= rule.threshold) or (rule.rule_type == "portfolio_value_below" and current.total_ton <= rule.threshold) or (rule.rule_type == "portfolio_change_percent" and abs(change) >= rule.threshold)
        if not triggered: continue
        recent = await session.scalar(select(AlertEvent).where(AlertEvent.rule_id == rule.id, AlertEvent.created_at >= datetime.now(timezone.utc) - timedelta(minutes=5)).limit(1))
        if recent is not None: continue
        session.add(AlertEvent(rule_id=rule.id, user_id=user_id, message=f"Portfolio {rule.rule_type.replace('_', ' ')}: {current.total_ton} TON ({change:+.2f}%)", observed_value=current.total_ton)); count += 1
    return count
