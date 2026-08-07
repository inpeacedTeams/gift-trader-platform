from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, utc_now

class Trade(Base):
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(primary_key=True)
    gift_id: Mapped[int] = mapped_column(ForeignKey("gifts.id"), index=True)
    marketplace: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str] = mapped_column(String(255))
    price_ton: Mapped[Decimal] = mapped_column(Numeric(24, 9))
    seller: Mapped[str | None] = mapped_column(String(255))
    buyer: Mapped[str | None] = mapped_column(String(255))
    traded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_url: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("marketplace", "external_id", name="uq_trade_source_id"),)

class SourceStatus(Base):
    __tablename__ = "source_statuses"
    id: Mapped[int] = mapped_column(primary_key=True)
    marketplace: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_error: Mapped[str | None] = mapped_column(Text)
    listings_count: Mapped[int] = mapped_column(default=0)
