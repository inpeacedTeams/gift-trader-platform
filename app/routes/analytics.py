from fastapi import APIRouter, Query
from app.core.config import get_settings
from app.market.analytics import overview
from app.market.collector import collect
from app.market.registry import build_parsers

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/overview")
async def market_overview(collection: list[str] = Query(default=[])):
    settings = get_settings()
    result = await collect(build_parsers(getgems_collections=collection or settings.getgems_collection_list, settings=settings))
    data = overview(result.snapshots)
    return {"data_mode": "live-only", **data.model_dump(), "unavailable": result.unavailable}
