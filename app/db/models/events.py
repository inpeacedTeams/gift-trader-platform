from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class MarketEvent(Base):
    """Something changed on the market.

    Snapshots answer "what is the price now", events answer "what just
    happened", which is what a trader actually watches.
    """

    __tablename__ = "market_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    gift_id: Mapped[int] = mapped_column(ForeignKey("gifts.id", ondelete="CASCADE"), index=True)
    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id", ondelete="SET NULL"))
    marketplace: Mapped[str] = mapped_column(String(64), index=True)
    # listed | price_down | price_up | delisted
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    price_ton: Mapped[Decimal | None] = mapped_column(Numeric(24, 9))
    previous_ton: Mapped[Decimal | None] = mapped_column(Numeric(24, 9))
    change_percent: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    __table_args__ = (
        Index("ix_market_events_occurred", "occurred_at"),
        Index("ix_market_events_gift_time", "gift_id", "occurred_at"),
    )
