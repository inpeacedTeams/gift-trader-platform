from decimal import Decimal
from fastapi import APIRouter, Query
from app.market.collector import collect
from app.market.core import MarketplaceCosts, find_arbitrage
from app.market.registry import build_parsers

router = APIRouter(prefix="/arbitrage", tags=["arbitrage"])

@router.get("")
async def arbitrage(
    collection: list[str] = Query(default=[]),
    min_profit_ton: Decimal = Query(default=Decimal("0"), ge=0),
    min_profit_percent: Decimal = Query(default=Decimal("0"), ge=0),
    getgems_fee_percent: Decimal = Query(default=Decimal("2"), ge=0, lt=100),
    portals_fee_percent: Decimal = Query(default=Decimal("0"), ge=0, lt=100),
    fragment_fee_percent: Decimal = Query(default=Decimal("0"), ge=0, lt=100),
):
    result = await collect(build_parsers(getgems_collections=collection))
    costs = {"getgems": MarketplaceCosts(fee_percent=getgems_fee_percent), "portals": MarketplaceCosts(fee_percent=portals_fee_percent), "fragment": MarketplaceCosts(fee_percent=fragment_fee_percent)}
    return {"data_mode": "live-only", "opportunities": find_arbitrage(result.snapshots, costs, min_profit_ton=min_profit_ton, min_profit_percent=min_profit_percent), "unavailable": result.unavailable}
