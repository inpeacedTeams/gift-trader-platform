"""Replays a strategy over stored history and measures what happened.

Every number this returns is arithmetic over rows in our database. Nothing
is modelled, extrapolated or annualised, and a trade whose exit falls past
the end of our history is reported as unresolved rather than being counted
as a win or a loss.

The window is split in half by time and the halves are reported separately.
A single blended figure is the easiest way to be fooled: a rule tuned until
it looks good will always look good on the data it was tuned on.
"""

from dataclasses import asdict, dataclass, field
from statistics import mean, median

from app.market.economics import DEFAULT_GAS_TON, net_proceeds

from .dataset import Candidate, Dataset
from .strategy import Strategy

# Below these the sample describes coincidences, not a strategy.
MIN_HISTORY_DAYS = 3.0
MIN_TRADES = 12
MIN_OUT_OF_SAMPLE_TRADES = 5
GAS_TON = float(DEFAULT_GAS_TON)
# A handful of real trades ship with the result so the headline number can
# be inspected rather than trusted.
EXAMPLE_COUNT = 5


@dataclass(frozen=True)
class SimTrade:
    listing_id: int
    gift_id: int
    gift_name: str | None
    marketplace: str
    entry_at: float
    entry_price: float
    exit_price: float
    net_proceeds: float
    profit_ton: float
    profit_percent: float
    hold_hours: float
    sold: bool


@dataclass
class Metrics:
    trades: int = 0
    wins: int = 0
    win_rate: float | None = None
    median_profit_percent: float | None = None
    mean_profit_percent: float | None = None
    total_profit_ton: float = 0.0
    median_hold_hours: float | None = None
    best_percent: float | None = None
    worst_percent: float | None = None
    # Entries whose exit lands beyond the end of our history.
    unresolved: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class BacktestResult:
    status: str
    strategy: Strategy
    window_days: int
    history_days: float
    overall: Metrics = field(default_factory=Metrics)
    in_sample: Metrics = field(default_factory=Metrics)
    out_of_sample: Metrics = field(default_factory=Metrics)
    # True only when the half the strategy was not chosen on also pays.
    holds_up: bool = False
    reason: str | None = None
    examples: list[SimTrade] = field(default_factory=list)


def _matches(candidate: Candidate, strategy: Strategy) -> bool:
    rules = strategy.filters
    if rules.collection_id is not None and candidate.collection_id != rules.collection_id:
        return False
    if rules.marketplaces and candidate.marketplace not in rules.marketplaces:
        return False
    if rules.min_price_ton is not None and candidate.entry_price < rules.min_price_ton:
        return False
    if rules.max_price_ton is not None and candidate.entry_price > rules.max_price_ton:
        return False
    if (
        rules.min_discount_percent is not None
        and candidate.discount_percent < rules.min_discount_percent
    ):
        return False
    if rules.max_rarity_percent is not None:
        # Unknown rarity is not common rarity. A rule about scarcity cannot be
        # satisfied by a gift whose scarcity we never learned.
        if candidate.rarity_percent is None or candidate.rarity_percent > rules.max_rarity_percent:
            return False
    if rules.min_closed_listings is not None and candidate.prior_closed < rules.min_closed_listings:
        return False
    if rules.max_hours_to_sell is not None:
        if candidate.prior_median_hours is None:
            return False
        if candidate.prior_median_hours > rules.max_hours_to_sell:
            return False
    return True


def _simulate_one(
    candidate: Candidate, strategy: Strategy, data: Dataset
) -> tuple[SimTrade | None, bool]:
    """Returns the trade, and whether it was left unresolved.

    Unresolved means the exit time is past the last thing we observed. It is
    excluded from every average: a trade still open is not a flat trade.
    """
    exit_at = candidate.entry_at + strategy.hold_hours * 3600.0
    if not data.has_data_after(candidate.gift_id, exit_at):
        return None, True
    exit_price = data.price_at(candidate.gift_id, exit_at, strategy.exit_at)
    if exit_price is None or exit_price <= 0:
        return None, True
    sold = candidate.closed_at is not None and candidate.closed_at <= exit_at
    if strategy.require_sold and not sold:
        return None, False
    proceeds = float(net_proceeds(candidate.marketplace, exit_price))
    cost = candidate.entry_price + GAS_TON
    profit = proceeds - cost
    return (
        SimTrade(
            listing_id=candidate.listing_id,
            gift_id=candidate.gift_id,
            gift_name=candidate.gift_name,
            marketplace=candidate.marketplace,
            entry_at=candidate.entry_at,
            entry_price=round(candidate.entry_price, 3),
            exit_price=round(exit_price, 3),
            net_proceeds=round(proceeds, 3),
            profit_ton=round(profit, 3),
            profit_percent=round(profit / cost * 100.0, 2) if cost > 0 else 0.0,
            hold_hours=float(strategy.hold_hours),
            sold=sold,
        ),
        False,
    )


def _measure(trades: list[SimTrade], unresolved: int) -> Metrics:
    if not trades:
        return Metrics(unresolved=unresolved)
    percents = [trade.profit_percent for trade in trades]
    wins = sum(1 for value in percents if value > 0)
    return Metrics(
        trades=len(trades),
        wins=wins,
        win_rate=round(wins / len(trades) * 100.0, 1),
        median_profit_percent=round(median(percents), 2),
        mean_profit_percent=round(mean(percents), 2),
        total_profit_ton=round(sum(trade.profit_ton for trade in trades), 3),
        median_hold_hours=round(median(trade.hold_hours for trade in trades), 1),
        best_percent=round(max(percents), 2),
        worst_percent=round(min(percents), 2),
        unresolved=unresolved,
    )


def run_backtest(data: Dataset, strategy: Strategy, split_at: float | None = None) -> BacktestResult:
    result = BacktestResult(
        status="ok",
        strategy=strategy,
        window_days=data.window_days,
        history_days=data.history_days,
    )
    if data.history_days < MIN_HISTORY_DAYS:
        result.status = "insufficient"
        result.reason = (
            f"Нужно минимум {MIN_HISTORY_DAYS:g} дней истории цен, "
            f"сейчас {data.history_days:g}. База наполняется с каждым проходом парсеров."
        )
        return result

    boundary = split_at if split_at is not None else midpoint(data)
    trades: list[SimTrade] = []
    early: list[SimTrade] = []
    late: list[SimTrade] = []
    unresolved = 0
    unresolved_early = 0
    unresolved_late = 0

    for candidate in data.candidates:
        if not _matches(candidate, strategy):
            continue
        trade, pending = _simulate_one(candidate, strategy, data)
        if pending:
            unresolved += 1
            if candidate.entry_at < boundary:
                unresolved_early += 1
            else:
                unresolved_late += 1
            continue
        if trade is None:
            continue
        trades.append(trade)
        (early if candidate.entry_at < boundary else late).append(trade)

    result.overall = _measure(trades, unresolved)
    result.in_sample = _measure(early, unresolved_early)
    result.out_of_sample = _measure(late, unresolved_late)
    result.holds_up = (
        result.out_of_sample.trades >= MIN_OUT_OF_SAMPLE_TRADES
        and (result.out_of_sample.median_profit_percent or 0) > 0
    )
    # Worst first: the losing trades are the ones worth reading.
    result.examples = sorted(trades, key=lambda trade: trade.profit_percent)[:EXAMPLE_COUNT]

    if result.overall.trades < MIN_TRADES:
        result.status = "insufficient"
        result.reason = (
            f"Всего {result.overall.trades} сделок под эти условия, нужно хотя бы {MIN_TRADES}. "
            "Ослабьте фильтры или подождите, пока накопится история."
        )
    return result


def midpoint(data: Dataset) -> float:
    """Chronological halfway point of the observed history."""
    if data.first_at is None or data.last_at is None:
        return 0.0
    return data.first_at + (data.last_at - data.first_at) / 2.0
