from decimal import Decimal

from fastapi import APIRouter

from app.db.repositories.arbitrage import DEFAULT_FEES, DEFAULT_GAS_TON
from app.schemas.fees import FeeSchedule, MarketplaceFee

router = APIRouter(prefix="/fees", tags=["fees"])

# Matches the fallback inside ArbitrageRepository._net_sale for venues that
# are not listed explicitly.
DEFAULT_SELL_FEE = Decimal("5")


@router.get("", response_model=FeeSchedule)
async def fee_schedule() -> FeeSchedule:
    """The cost side of a flip, straight from the arbitrage constants.

    Same source as the spread scanner, so the calculator on a gift page and
    the opportunities list can never disagree about what a trade costs.
    """
    return FeeSchedule(
        gas_ton=DEFAULT_GAS_TON,
        default_sell_fee_percent=DEFAULT_SELL_FEE,
        marketplaces=[
            MarketplaceFee(marketplace=name, sell_fee_percent=fee)
            for name, fee in sorted(DEFAULT_FEES.items())
        ],
    )
