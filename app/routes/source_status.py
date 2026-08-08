from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.repositories import SourceStatusRepository
from app.db.session import get_session
from app.schemas.frontend import SourceStatusCard, SourceStatusList

router = APIRouter(prefix="/sources", tags=["sources"])

# Sources that cannot run without a credential we may not have.
CREDENTIAL_REQUIRED = {
    "portals": ("portals_auth_data",),
    "mrkt": ("mrkt_token", "mrkt_init_data"),
}


def _is_configured(marketplace: str) -> bool:
    settings_names = CREDENTIAL_REQUIRED.get(marketplace)
    if settings_names is None:
        return True
    settings = get_settings()
    return any(getattr(settings, name, None) for name in settings_names)


@router.get("/status", response_model=SourceStatusList)
async def source_status(session: AsyncSession = Depends(get_session)):
    """Per source health from the last crawl, plus the sources we never ran.

    A source that is switched off is not the same as a source that is broken,
    and the interface should never claim a collector is live when it is not.
    """
    settings = get_settings()
    recorded = {item.marketplace: item for item in await SourceStatusRepository(session).list()}
    cutoff = datetime.now(timezone.utc) - timedelta(
        seconds=settings.market_sync_interval_seconds * 3
    )
    cards: list[SourceStatusCard] = []
    for marketplace in settings.market_source_list:
        item = recorded.pop(marketplace, None)
        if item is None:
            cards.append(
                SourceStatusCard(
                    marketplace=marketplace,
                    status="pending",
                    configured=_is_configured(marketplace),
                    last_error="no crawl recorded yet",
                )
            )
            continue
        attempted = item.last_attempt_at
        cards.append(
            SourceStatusCard(
                marketplace=marketplace,
                status=item.status,
                configured=_is_configured(marketplace),
                stale=bool(attempted and attempted < cutoff),
                listings_count=item.listings_count,
                last_attempt_at=item.last_attempt_at,
                last_success_at=item.last_success_at,
                last_error=item.last_error,
            )
        )
    # Anything recorded but no longer enabled, so history is not hidden.
    for item in recorded.values():
        cards.append(
            SourceStatusCard(
                marketplace=item.marketplace,
                status="disabled",
                configured=_is_configured(item.marketplace),
                listings_count=item.listings_count,
                last_attempt_at=item.last_attempt_at,
                last_success_at=item.last_success_at,
                last_error=item.last_error,
            )
        )
    return SourceStatusList(sources=cards)
