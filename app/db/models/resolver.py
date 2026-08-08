from datetime import datetime
from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, utc_now

class ResolverTelemetry(Base):
    __tablename__ = "resolver_telemetry"
    id: Mapped[int] = mapped_column(primary_key=True)
    nft_address: Mapped[str] = mapped_column(String(128), index=True)
    collection_address: Mapped[str | None] = mapped_column(String(128), index=True)
    outcome: Mapped[str] = mapped_column(String(32), index=True)
    method: Mapped[str] = mapped_column(String(64))
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float | None] = mapped_column()
    metadata_name: Mapped[str | None] = mapped_column(String(255))
    metadata_model: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    __table_args__ = (Index("ix_resolver_telemetry_outcome_time", "outcome", "created_at"),)
