from fastapi import APIRouter, Query
from app.market.registry import build_parsers
from app.market.models import SourceUnavailable

router = APIRouter(prefix="/markets", tags=["markets"])

@router.get("/snapshots")
async def snapshots(collection: list[str] = Query(default=[]), portals_endpoint: str = "https://portal-market.com/api"):
    results = []
    for parser in build_parsers(getgems_collections=collection, portals_endpoint=portals_endpoint):
        try:
            snapshot = await parser.snapshot()
            results.append({"marketplace": snapshot.marketplace, "observed_at": snapshot.observed_at, "listings": snapshot.listings})
        except SourceUnavailable as exc:
            results.append({"marketplace": exc.marketplace, "status": "unavailable", "error": exc.reason, "listings": []})
    return {"data_mode": "live-only", "markets": results}
