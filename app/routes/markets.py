from fastapi import APIRouter, Query
from app.core.config import get_settings
from app.market.collector import collect
from app.market.health import health_from_error, health_from_snapshot, health_to_dict
from app.market.registry import build_parsers
from app.schemas.market import MarketsResponse

router = APIRouter(prefix="/markets", tags=["markets"])


def _parsers(collection: list[str], portals_endpoint: str | None):
    settings = get_settings()
    return build_parsers(getgems_collections=collection, portals_endpoint=portals_endpoint or settings.portals_endpoint, settings=settings)


@router.get("/snapshots", response_model=MarketsResponse)
async def snapshots(collection: list[str] = Query(default=[]), portals_endpoint: str | None = None):
    result = await collect(_parsers(collection, portals_endpoint))
    unavailable = [{"marketplace": item["marketplace"], "error": item["reason"], "listings": []} for item in result.unavailable]
    return MarketsResponse(markets=[snapshot.model_dump() for snapshot in result.snapshots], unavailable=unavailable)


@router.get("/health")
async def source_health(collection: list[str] = Query(default=[]), portals_endpoint: str | None = None):
    result = await collect(_parsers(collection, portals_endpoint))
    health = [health_from_snapshot(snapshot) for snapshot in result.snapshots]
    health.extend(health_from_error(item["marketplace"], item["reason"]) for item in result.unavailable)
    return {"data_mode": "live-only", "sources": [health_to_dict(item) for item in health]}
