from fastapi import APIRouter, Query
from app.core.config import get_settings
from app.market.collector import collect
from app.market.models import SourceUnavailable
from app.market.registry import build_parsers
from app.schemas.market import MarketsResponse

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("/snapshots", response_model=MarketsResponse)
async def snapshots(
    collection: list[str] = Query(default=[]),
    portals_endpoint: str | None = None,
):
    settings = get_settings()
    result = await collect(build_parsers(
        getgems_collections=collection,
        portals_endpoint=portals_endpoint or settings.portals_endpoint,
    ))
    unavailable = [{"marketplace": item["marketplace"], "error": item["reason"], "listings": []} for item in result.unavailable]
    return MarketsResponse(
        markets=[snapshot.model_dump() for snapshot in result.snapshots],
        unavailable=unavailable,
    )
