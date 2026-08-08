from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, Listing
from app.market.economics import (
    DEFAULT_FEES,
    DEFAULT_GAS_TON,
    DEFAULT_SELL_FEE,
    net_proceeds,
)

# Re-exported: several call sites import the fee table from here.
__all__ = ["ArbitrageRepository", "DEFAULT_FEES", "DEFAULT_GAS_TON", "DEFAULT_SELL_FEE"]


class ArbitrageRepository:
    """Cross marketplace spreads computed from stored listings.

    This used to crawl every marketplace on request, which meant a page load
    could take minutes. The sync worker already keeps the book fresh, so the
    read path just reads.
    """

    def __init__(self, session: AsyncSession, fees: dict[str, Decimal] | None = None):
        self.session = session
        self.fees = fees or DEFAULT_FEES

    def _net_sale(self, marketplace: str, price: Decimal) -> Decimal:
        if self.fees is DEFAULT_FEES:
            return net_proceeds(marketplace, price)
        fee = self.fees.get(marketplace, DEFAULT_SELL_FEE)
        return price - price * fee / Decimal(100)

    async def opportunities(
        self,
        *,
        min_profit_ton: Decimal = Decimal("0"),
        min_profit_percent: Decimal = Decimal("0"),
        gas_ton: Decimal = DEFAULT_GAS_TON,
        limit: int = 50,
    ) -> list[dict]:
        rows = (
            await self.session.execute(
                select(
                    Gift.id,
                    Gift.name,
                    Gift.model,
                    Gift.image_url,
                    Collection.name.label("collection_name"),
                    Listing.id.label("listing_id"),
                    Listing.marketplace,
                    Listing.price_ton,
                    Listing.url,
                )
                .join(Listing, (Listing.gift_id == Gift.id) & Listing.active.is_(True))
                .outerjoin(Collection, Collection.id == Gift.collection_id)
                .order_by(Gift.id, Listing.price_ton.asc())
            )
        ).all()

        by_gift: dict[int, list] = {}
        for row in rows:
            by_gift.setdefault(row.id, []).append(row)

        found: list[dict] = []
        for listings in by_gift.values():
            venues = {}
            for row in listings:
                # Listings are price ordered, so the first per venue is its floor.
                venues.setdefault(row.marketplace, row)
            if len(venues) < 2:
                continue
            ordered = sorted(venues.values(), key=lambda row: row.price_ton)
            buy, sell = ordered[0], ordered[-1]
            if buy.marketplace == sell.marketplace:
                continue
            cost = buy.price_ton + gas_ton
            revenue = self._net_sale(sell.marketplace, sell.price_ton)
            profit = revenue - cost
            percent = profit / cost * Decimal(100) if cost else Decimal(0)
            if profit < min_profit_ton or percent < min_profit_percent:
                continue
            found.append(
                {
                    "gift_id": buy.id,
                    "name": buy.name,
                    "model": buy.model,
                    "image_url": buy.image_url,
                    "collection_name": buy.collection_name,
                    "buy_marketplace": buy.marketplace,
                    "sell_marketplace": sell.marketplace,
                    "buy_price_ton": buy.price_ton,
                    "sell_price_ton": sell.price_ton,
                    "buy_url": buy.url,
                    "sell_url": sell.url,
                    "profit_ton": profit.quantize(Decimal("0.001")),
                    "profit_percent": percent.quantize(Decimal("0.01")),
                }
            )
        found.sort(key=lambda item: item["profit_ton"], reverse=True)
        return found[:limit]
