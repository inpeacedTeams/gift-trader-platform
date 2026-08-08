import logging
from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.db.repositories.trades import TradeRepository
from app.db.session import SessionLocal
from app.market.history import TonnelSaleHistory
from app.market.http import MarketHttp
from app.market.models import SourceUnavailable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TradeSyncReport:
    fetched: int
    stored: int
    unavailable: str | None = None


async def sync_trades(settings: Settings | None = None) -> TradeSyncReport:
    """Pull completed sales and store the ones we have not seen yet."""
    settings = settings or get_settings()
    http = MarketHttp(
        timeout=settings.source_timeout_seconds,
        retries=settings.source_retries,
        backoff_seconds=settings.source_backoff_seconds,
    )
    collector = TonnelSaleHistory(
        http, settings.tonnel_history_endpoint, auth_data=settings.tonnel_auth_data
    )
    try:
        trades = await collector.fetch()
    except SourceUnavailable as exc:
        logger.info("trade sync skipped", extra={"reason": exc.reason})
        return TradeSyncReport(0, 0, exc.reason)
    async with SessionLocal() as session:
        stored = await TradeRepository(session).persist(trades)
    logger.info("trade sync complete", extra={"fetched": len(trades), "stored": stored})
    return TradeSyncReport(len(trades), stored)
