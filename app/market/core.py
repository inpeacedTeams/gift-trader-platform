from collections import defaultdict
from decimal import Decimal
from pydantic import BaseModel, Field
from .models import Listing, MarketSnapshot

class MarketplaceCosts(BaseModel):
    fee_percent: Decimal = Field(default=Decimal("0"), ge=0, lt=100)
    fixed_ton: Decimal = Field(default=Decimal("0"), ge=0)
    def total(self, price_ton: Decimal) -> Decimal:
        return price_ton * self.fee_percent / Decimal("100") + self.fixed_ton

class ArbitrageOpportunity(BaseModel):
    gift_key: str
    buy_marketplace: str
    sell_marketplace: str
    buy_listing_id: str
    sell_listing_id: str
    buy_price_ton: Decimal
    sell_price_ton: Decimal
    buy_cost_ton: Decimal
    sell_revenue_ton: Decimal
    profit_ton: Decimal
    profit_percent: Decimal
    observed_at: str

def gift_key(listing: Listing) -> str:
    if listing.collection_id:
        return f"collection:{listing.collection_id}:gift:{listing.gift_id}"
    return f"gift:{listing.gift_id}"

def find_arbitrage(snapshots: list[MarketSnapshot], costs: dict[str, MarketplaceCosts], *, min_profit_ton: Decimal = Decimal("0"), min_profit_percent: Decimal = Decimal("0")) -> list[ArbitrageOpportunity]:
    grouped: dict[str, list[Listing]] = defaultdict(list)
    for snapshot in snapshots:
        for listing in snapshot.listings:
            grouped[gift_key(listing)].append(listing)
    opportunities: list[ArbitrageOpportunity] = []
    for key, listings in grouped.items():
        for buy in listings:
            for sell in listings:
                if buy.marketplace == sell.marketplace or buy.price_ton >= sell.price_ton:
                    continue
                buy_cost = buy.price_ton + costs.get(buy.marketplace, MarketplaceCosts()).total(buy.price_ton)
                sell_revenue = sell.price_ton - costs.get(sell.marketplace, MarketplaceCosts()).total(sell.price_ton)
                profit = sell_revenue - buy_cost
                percent = profit / buy_cost * Decimal("100") if buy_cost else Decimal("0")
                if profit < min_profit_ton or percent < min_profit_percent:
                    continue
                opportunities.append(ArbitrageOpportunity(gift_key=key, buy_marketplace=buy.marketplace, sell_marketplace=sell.marketplace, buy_listing_id=buy.listing_id, sell_listing_id=sell.listing_id, buy_price_ton=buy.price_ton, sell_price_ton=sell.price_ton, buy_cost_ton=buy_cost, sell_revenue_ton=sell_revenue, profit_ton=profit, profit_percent=percent, observed_at=max(buy.observed_at, sell.observed_at).isoformat()))
    return sorted(opportunities, key=lambda item: item.profit_ton, reverse=True)
