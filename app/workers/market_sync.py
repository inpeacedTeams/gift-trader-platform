import logging
from dataclasses import dataclass
from app.core.config import Settings, get_settings
from app.db.repositories import MarketSnapshotRepository, SourceStatusRepository
from app.db.session import SessionLocal
from app.market.collector import collect
from app.market.registry import build_parsers

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class SyncReport:
    snapshots: int
    listings: int
    unavailable: int

async def sync_market(settings: Settings | None = None) -> SyncReport:
    settings = settings or get_settings()
    result = await collect(build_parsers(getgems_collections=settings.getgems_collection_addresses, settings=settings))
    async with SessionLocal() as session:
        snapshot_repo = MarketSnapshotRepository(session)
        status_repo = SourceStatusRepository(session)
        listings = 0
        for snapshot in result.snapshots:
            listings += await snapshot_repo.persist(snapshot)
            await status_repo.record_success(snapshot.marketplace, len(snapshot.listings))
        for item in result.unavailable:
            await status_repo.record_failure(item["marketplace"], item["reason"])
        await session.commit()
    report = SyncReport(len(result.snapshots), listings, len(result.unavailable))
    logger.info("market sync complete", extra={"snapshots": report.snapshots, "listings": report.listings, "unavailable": report.unavailable})
    return report
