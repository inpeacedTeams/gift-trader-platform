from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now

class Listing(Base):
    __tablename__ = "listings"
    id: Mapped[int] = mapped_column(primary_key=True)
    gift_id: Mapped[int] = mapped_column(ForeignKey("gifts.id"), index=True)
    marketplace: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str] = mapped_column(String(255))
    price_ton: Mapped[Decimal] = mapped_column(Numeric(24, 9))
    seller: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(Text)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    active: Mapped[bool] = mapped_column(default=True)
    gift: Mapped["Gift"] = relationship(back_populates="listings")
    __table_args__ = (UniqueConstraint("marketplace", "external_id", name="uq_listing_source_id"), Index("ix_listings_active_price", "active", "price_ton"))

class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    gift_id: Mapped[int] = mapped_column(ForeignKey("gifts.id"), index=True)
    marketplace: Mapped[str] = mapped_column(String(64), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    floor_ton: Mapped[Decimal | None] = mapped_column(Numeric(24, 9))
    median_ton: Mapped[Decimal | None] = mapped_column(Numeric(24, 9))
    volume_ton: Mapped[Decimal | None] = mapped_column(Numeric(24, 9))
    listings_count: Mapped[int] = mapped_column(default=0)
    source_url: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (Index("ix_price_history_gift_market_time", "gift_id", "marketplace", "observed_at"),)

from .gifts import Gift
