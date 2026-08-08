from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class Position(Base):
    """A gift the user actually bought.

    Entered by hand: marketplaces publish listings, not who paid what, so the
    cost basis has to come from the trader. Everything else (current value,
    profit, win rate) is derived from it and never stored, so it cannot go
    stale against the live book.
    """

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    gift_id: Mapped[int] = mapped_column(ForeignKey("gifts.id", ondelete="CASCADE"), index=True)
    # Where it was bought. Kept because the exit fee depends on the venue.
    marketplace: Mapped[str | None] = mapped_column(String(64))
    buy_price_ton: Mapped[Decimal] = mapped_column(Numeric(24, 9))
    quantity: Mapped[int] = mapped_column(default=1)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    # Set on close. A position with no sale price is still open, whatever the
    # user typed elsewhere.
    sell_price_ton: Mapped[Decimal | None] = mapped_column(Numeric(24, 9))
    sell_marketplace: Mapped[str | None] = mapped_column(String(64))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_positions_user_open", "user_id", "closed_at"),)
