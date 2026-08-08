from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class SellerIdentity(Base):
    """A seller handle that belongs to this user.

    Marketplaces publish who is selling a lot, and both Tonnel and MRKT do it
    with a Telegram user id. Since sign in is Telegram, that id is already
    known, so a user's own listings can be recognised without asking them to
    prove anything.

    `marketplace` is NULL when the handle is valid everywhere, which is the
    case for a Telegram id. A venue that invents its own seller key gets its
    own row, entered by hand.
    """

    __tablename__ = "seller_identities"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    marketplace: Mapped[str | None] = mapped_column(String(64))
    seller: Mapped[str] = mapped_column(String(255))
    # "telegram" is derived from the login, "manual" was typed in. Only the
    # first is trustworthy, and the interface says which is which.
    source: Mapped[str] = mapped_column(String(16), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (Index("ix_seller_identities_seller", "seller"),)


class UndercutNotice(Base):
    """The last time we told someone their lot had been undercut.

    Without this the same rival listing would be announced on every crawl.
    Keeping the rival price means a second warning only goes out when the
    competition actually moved lower, not because time passed.
    """

    __tablename__ = "undercut_notices"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), unique=True
    )
    my_price_ton: Mapped[Decimal] = mapped_column(Numeric(24, 9))
    rival_price_ton: Mapped[Decimal] = mapped_column(Numeric(24, 9))
    notified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (UniqueConstraint("listing_id", name="uq_undercut_listing"),)
