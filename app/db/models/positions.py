from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class Position(Base):
    """A gift someone actually bought, and what it cost them.

    The wallet sync can see what an address holds, but not the price paid for
    it, and the price paid is the only number that turns a chart into a
    profit or a loss. So this is entered by hand and never guessed.

    Closing a position keeps the row: a sold flip is the record of whether
    the thesis worked, which is worth more than a clean list of open lots.
    """

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    gift_id: Mapped[int] = mapped_column(ForeignKey("gifts.id"), index=True)
    buy_price_ton: Mapped[Decimal] = mapped_column(Numeric(24, 9))
    buy_marketplace: Mapped[str | None] = mapped_column(String(64))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    sell_price_ton: Mapped[Decimal | None] = mapped_column(Numeric(24, 9))
    sell_marketplace: Mapped[str | None] = mapped_column(String(64))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        # Open lots are read on every page load, closed ones only on demand.
        Index("ix_positions_user_open", "user_id", "closed_at"),
    )
