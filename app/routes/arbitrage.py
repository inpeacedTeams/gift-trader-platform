from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.arbitrage import DEFAULT_GAS_TON, ArbitrageRepository
from app.db.session import get_session
from app.schemas.frontend import ArbitrageList, ArbitrageOpportunity

router = APIRouter(prefix="/arbitrage", tags=["arbitrage"])


@router.get("", response_model=ArbitrageList)
async def arbitrage(
    min_profit_ton: Decimal = Query(default=Decimal("0"), ge=0),
    min_profit_percent: Decimal = Query(default=Decimal("0"), ge=0),
    gas_ton: Decimal = Query(default=DEFAULT_GAS_TON, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """Fee aware spreads between marketplaces, from stored listings."""
    rows = await ArbitrageRepository(session).opportunities(
        min_profit_ton=min_profit_ton,
        min_profit_percent=min_profit_percent,
        gas_ton=gas_ton,
        limit=limit,
    )
    return ArbitrageList(items=[ArbitrageOpportunity(**row) for row in rows])
