from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, utc_now

class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"
    id: Mapped[int] = mapped_column(primary_key=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("portfolio_wallets.id", ondelete="CASCADE"), index=True)
    nft_address: Mapped[str] = mapped_column(String(128))
    collection_address: Mapped[str | None] = mapped_column(String(128))
    name: Mapped[str | None] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(Text)
    estimated_price_ton: Mapped[Decimal | None] = mapped_column(Numeric(24, 9))
    valuation_source: Mapped[str] = mapped_column(String(64), default="unresolved")
    valuation_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (UniqueConstraint("wallet_id", "nft_address", name="uq_portfolio_wallet_nft"), Index("ix_portfolio_holdings_wallet_time", "wallet_id", "observed_at"))

class PortfolioValuation(Base):
    __tablename__ = "portfolio_valuations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    total_ton: Mapped[Decimal] = mapped_column(Numeric(24, 9))
    ton_balance: Mapped[Decimal] = mapped_column(Numeric(24, 9))
    nft_value_ton: Mapped[Decimal] = mapped_column(Numeric(24, 9))
    asset_count: Mapped[int] = mapped_column(default=0)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    __table_args__ = (Index("ix_portfolio_valuations_user_time", "user_id", "observed_at"),)
