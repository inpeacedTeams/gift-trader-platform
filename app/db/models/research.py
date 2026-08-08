from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class SavedStrategy(Base):
    """A rule set a user kept.

    The definition is stored as JSON rather than as columns because the
    schema of a strategy is expected to grow, and a saved strategy must keep
    meaning exactly what it meant when it was measured. Spreading it across
    typed columns would quietly rewrite old strategies every migration.
    """

    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    # "discovered" from the grid, "ai" from a request in words, "manual".
    source: Mapped[str] = mapped_column(String(16), default="manual")
    definition: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (Index("ix_strategies_user_created", "user_id", "created_at"),)


class StrategyRun(Base):
    """One measurement of one strategy.

    Kept so a claim made a week ago can be checked against the history that
    existed then. A backtest re-run on more data is a different result, and
    overwriting the old one would hide that it changed.
    """

    __tablename__ = "strategy_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), index=True
    )
    window_days: Mapped[int] = mapped_column()
    history_days: Mapped[float] = mapped_column(Numeric(8, 2))
    trades: Mapped[int] = mapped_column(default=0)
    median_profit_percent: Mapped[float | None] = mapped_column(Numeric(10, 2))
    out_of_sample_percent: Mapped[float | None] = mapped_column(Numeric(10, 2))
    holds_up: Mapped[bool] = mapped_column(default=False)
    metrics: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
