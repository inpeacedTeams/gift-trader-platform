from datetime import datetime, timezone
from dataclasses import dataclass

@dataclass
class SourceHealth:
    marketplace: str
    status: str
    last_attempt_at: datetime
    last_success_at: datetime | None = None
    last_error: str | None = None
    listings_count: int = 0

    @classmethod
    def success(cls, marketplace: str, listings_count: int) -> "SourceHealth":
        now = datetime.now(timezone.utc)
        return cls(marketplace=marketplace, status="healthy", last_attempt_at=now, last_success_at=now, listings_count=listings_count)

    @classmethod
    def failure(cls, marketplace: str, error: str) -> "SourceHealth":
        return cls(marketplace=marketplace, status="unavailable", last_attempt_at=datetime.now(timezone.utc), last_error=error)
