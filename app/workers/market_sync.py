import logging
from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.db.repositories import MarketSnapshotRepository, SourceStatusRepository
from app.db.session import SessionLocal
from app.market.collector import collect
from app.market.registry import build_parsers
from app.notifications.alerts import GiftAlertEvaluator
from app.notifications.undercut import UndercutEvaluator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SyncReport:
    snapshots: int
    listings: int
    unavailable: int
    alerts: int = 0
    undercuts: int = 0


async def sync_market(settings: Settings | None = None) -> SyncReport:
    settings = settings or get_settings()
    result = await collect(
        build_parsers(getgems_collections=settings.getgems_collection_list, settings=settings)
    )
    async with SessionLocal() as session:
        snapshot_repo = MarketSnapshotRepository(session)
        status_repo = SourceStatusRepository(session)
        listings = 0
        touched: set[int] = set()
        for snapshot in result.snapshots:
            persisted = await snapshot_repo.persist(snapshot)
            listings += persisted.listings
            touched |= persisted.gift_ids
            await status_repo.record_success(snapshot.marketplace, len(snapshot.listings))
        for item in result.unavailable:
            await status_repo.record_failure(item["marketplace"], item["reason"])
        # Prices are final for this pass, so rules see the true cross market floor.
        alerts = await GiftAlertEvaluator(session).evaluate(touched)
        # Sellers care about the same pass from the other side of the book.
        undercuts = await UndercutEvaluator(session).evaluate()
        await session.commit()
    report = SyncReport(
        len(result.snapshots), listings, len(result.unavailable), alerts, undercuts
    )
    logger.info(
        "market sync complete",
        extra={
            "snapshots": report.snapshots,
            "listings": report.listings,
            "unavailable": report.unavailable,
            "alerts": report.alerts,
            "undercuts": report.undercuts,
        },
    )
    return report
