from datetime import datetime
from pydantic import BaseModel, ConfigDict, HttpUrl
from app.market.models import Listing


class UnavailableSource(BaseModel):
    marketplace: str
    status: str = "unavailable"
    error: str
    listings: list[Listing] = []


class MarketSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    marketplace: str
    observed_at: datetime
    listings: list[Listing]
    source_url: HttpUrl


class MarketsResponse(BaseModel):
    data_mode: str = "live-only"
    markets: list[MarketSnapshotResponse]
    unavailable: list[UnavailableSource] = []
