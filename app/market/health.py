from dataclasses import dataclass
from datetime import datetime, timezone
from .models import MarketSnapshot

@dataclass(frozen=True)
class SourceHealth:
    marketplace: str
    status: str
    observed_at: datetime | None
    listings_count: int
    error: str | None = None


def health_from_snapshot(snapshot: MarketSnapshot) -> SourceHealth:
    return SourceHealth(snapshot.marketplace, "ok", snapshot.observed_at, len(snapshot.listings))


def health_from_error(marketplace: str, error: str) -> SourceHealth:
    return SourceHealth(marketplace, "unavailable", None, 0, error)


def health_to_dict(item: SourceHealth) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    age_seconds = (now - item.observed_at).total_seconds() if item.observed_at else None
    return {"marketplace": item.marketplace, "status": item.status, "observed_at": item.observed_at, "age_seconds": age_seconds, "listings_count": item.listings_count, "error": item.error}
