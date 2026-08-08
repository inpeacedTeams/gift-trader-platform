"""What a strategy is, as data.

A strategy has to be a closed set of fields rather than free text, for two
reasons: the engine must be able to execute it without interpretation, and
an assistant proposing one must land inside something we can validate and
reject. Anything the schema cannot express, the backtest cannot honestly
measure, so the schema is the honest boundary of the feature.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

ExitPrice = Literal["floor", "median"]

# Guard rails on the search space. A strategy holding for a month cannot be
# validated on a database that is two weeks old.
MAX_HOLD_HOURS = 24 * 14
MIN_HOLD_HOURS = 1


class Filters(BaseModel):
    """Which listings the strategy would have bought.

    Every threshold is optional and every one is evaluated against what was
    known at the moment the listing appeared.
    """

    collection_id: int | None = None
    # Empty means every venue the crawler covers.
    marketplaces: list[str] = Field(default_factory=list)
    min_price_ton: float | None = Field(default=None, ge=0)
    max_price_ton: float | None = Field(default=None, gt=0)
    # How far under the gift's own prevailing price the lot was listed.
    min_discount_percent: float | None = Field(default=None, ge=0, lt=100)
    # Scarcity of the rarest trait, as a share of the collection. Smaller is
    # rarer, so this is a ceiling: "no more common than".
    max_rarity_percent: float | None = Field(default=None, gt=0, le=100)
    # Liquidity evidence, counted from listings that had already closed.
    max_hours_to_sell: float | None = Field(default=None, gt=0)
    min_closed_listings: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _coherent(self) -> "Filters":
        if (
            self.min_price_ton is not None
            and self.max_price_ton is not None
            and self.min_price_ton >= self.max_price_ton
        ):
            raise ValueError("min_price_ton must be below max_price_ton")
        return self

    def describe(self) -> list[str]:
        """Human readable conditions, for the UI and for prompts."""
        parts: list[str] = []
        if self.min_discount_percent is not None:
            parts.append(f"дешевле своей цены на {self.min_discount_percent:g}%+")
        if self.max_rarity_percent is not None:
            parts.append(f"редкость не хуже {self.max_rarity_percent:g}%")
        if self.max_hours_to_sell is not None:
            parts.append(f"продаётся быстрее {self.max_hours_to_sell:g} ч")
        if self.min_closed_listings is not None and self.min_closed_listings > 0:
            parts.append(f"не меньше {self.min_closed_listings} закрытых лотов в истории")
        if self.max_price_ton is not None:
            parts.append(f"до {self.max_price_ton:g} TON")
        if self.min_price_ton:
            parts.append(f"от {self.min_price_ton:g} TON")
        if self.marketplaces:
            parts.append("площадки: " + ", ".join(self.marketplaces))
        return parts


class Strategy(BaseModel):
    name: str = Field(default="Untitled", max_length=120)
    filters: Filters = Field(default_factory=Filters)
    hold_hours: int = Field(default=48, ge=MIN_HOLD_HOURS, le=MAX_HOLD_HOURS)
    exit_at: ExitPrice = "floor"
    # Only count entries whose listing actually left the book inside the hold
    # window. Stricter and smaller: evidence the lot was sellable at all.
    require_sold: bool = False

    def summary(self) -> str:
        conditions = ", ".join(self.filters.describe()) or "без фильтров"
        exit_label = "floor" if self.exit_at == "floor" else "медиане"
        return f"Покупать {conditions}; выход через {self.hold_hours} ч по {exit_label}"
