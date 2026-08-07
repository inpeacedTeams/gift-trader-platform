from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import SourceStatus

class SourceStatusRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_success(self, marketplace: str, listings_count: int) -> SourceStatus:
        now = datetime.now(timezone.utc)
        status = await self._get(marketplace)
        if status is None:
            status = SourceStatus(marketplace=marketplace)
            self.session.add(status)
        status.status = "ok"
        status.last_attempt_at = now
        status.last_success_at = now
        status.last_error = None
        status.listings_count = listings_count
        await self.session.flush()
        return status

    async def record_failure(self, marketplace: str, error: str) -> SourceStatus:
        now = datetime.now(timezone.utc)
        status = await self._get(marketplace)
        if status is None:
            status = SourceStatus(marketplace=marketplace)
            self.session.add(status)
        status.status = "unavailable"
        status.last_attempt_at = now
        status.last_error = error[:4000]
        await self.session.flush()
        return status

    async def list(self) -> list[SourceStatus]:
        return list((await self.session.scalars(select(SourceStatus).order_by(SourceStatus.marketplace))).all())

    async def _get(self, marketplace: str) -> SourceStatus | None:
        return await self.session.scalar(select(SourceStatus).where(SourceStatus.marketplace == marketplace))
