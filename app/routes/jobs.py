from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException

from app.core.config import get_settings
from app.workers.market_sync import sync_market
from app.workers.trade_sync import sync_trades

router = APIRouter(prefix="/jobs", tags=["jobs"])


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Crawls are expensive and hit third party rate limits.

    Left open, a loop over this endpoint is a denial of service against both
    us and every marketplace we read.
    """
    expected = get_settings().admin_token
    if not expected:
        raise HTTPException(503, "Manual jobs are disabled: set ADMIN_TOKEN")
    if x_admin_token != expected:
        raise HTTPException(403, "Admin token required")


@router.post("/market-sync", status_code=202, dependencies=[Depends(require_admin)])
async def trigger_market_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(sync_market)
    return {"status": "accepted", "job": "market-sync"}


@router.post("/trade-sync", status_code=202, dependencies=[Depends(require_admin)])
async def trigger_trade_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(sync_trades)
    return {"status": "accepted", "job": "trade-sync"}
