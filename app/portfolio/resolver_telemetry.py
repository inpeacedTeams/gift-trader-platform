from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import ResolverTelemetry

async def record_attempt(session: AsyncSession, *, nft_address: str, collection_address: str | None, outcome: str, method: str, candidate_count: int, confidence: float | None, metadata_name: str | None, metadata_model: str | None) -> None:
    session.add(ResolverTelemetry(nft_address=nft_address, collection_address=collection_address, outcome=outcome, method=method, candidate_count=candidate_count, confidence=confidence, metadata_name=metadata_name, metadata_model=metadata_model))

async def summary(session: AsyncSession) -> list[dict[str, object]]:
    rows = (await session.execute(select(ResolverTelemetry.outcome, func.count(ResolverTelemetry.id)).group_by(ResolverTelemetry.outcome).order_by(ResolverTelemetry.outcome))).all()
    return [{"outcome": outcome, "count": count} for outcome, count in rows]
