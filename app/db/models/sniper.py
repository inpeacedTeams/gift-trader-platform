from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class SniperWatch(Base):
    """A standing order to shout when something cheap appears.

    Every field is optional except the owner: an empty watch means the whole
    market, a filled one narrows it down.
    """

    __tablename__ = "sniper_watches"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    gift_name: Mapped[str | None] = mapped_column(String(255))
    model: Mapped[str | None] = mapped_column(String(255))
    max_price_ton: Mapped[Decimal | None] = mapped_column(Numeric(24, 9))
    min_discount_percent: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    marketplace: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (Index("ix_sniper_watches_active", "is_active", "user_id"),)


class SniperHit(Base):
    """Proof that a watch already fired on this listing."""

    __tablename__ = "sniper_hits"

    id: Mapped[int] = mapped_column(primary_key=True)
    watch_id: Mapped[int] = mapped_column(ForeignKey("sniper_watches.id", ondelete="CASCADE"), index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"))
    price_ton: Mapped[Decimal] = mapped_column(Numeric(24, 9))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (UniqueConstraint("watch_id", "listing_id", name="uq_sniper_hit"),)
