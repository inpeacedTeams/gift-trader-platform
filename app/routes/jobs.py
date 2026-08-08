from fastapi import APIRouter, BackgroundTasks

from app.workers.market_sync import sync_market
from app.workers.trade_sync import sync_trades

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/market-sync", status_code=202)
async def trigger_market_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(sync_market)
    return {"status": "accepted", "job": "market-sync"}


@router.post("/trade-sync", status_code=202)
async def trigger_trade_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(sync_trades)
    return {"status": "accepted", "job": "trade-sync"}
