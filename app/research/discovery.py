"""Searches the rule space for strategies that survive validation.

The search is a plain grid: every combination of a few sensible thresholds,
backtested. There is nothing clever about it, and that is the point. A
smarter optimiser on this much history would only find better ways to fit
noise.

Ranking happens on the first half of the window and reporting happens on the
second. A rule chosen because it was the best of fifty on one stretch of
data tells you nothing until it has been tried on a stretch it did not get
to pick.
"""

import itertools
from dataclasses import dataclass

from .backtest import BacktestResult, midpoint, run_backtest
from .dataset import Dataset
from .strategy import Filters, Strategy

# Kept deliberately coarse. Fine grained thresholds on a short history are
# how a backtest tool starts lying: there is always a cut that looks perfect.
DISCOUNT_STEPS = (5.0, 10.0, 20.0)
RARITY_STEPS = (None, 5.0, 1.0)
LIQUIDITY_STEPS = (None, 72.0, 24.0)
HOLD_STEPS = (24, 72)
MAX_RESULTS = 6


@dataclass
class Discovery:
    status: str
    tested: int
    history_days: float
    window_days: int
    results: list[BacktestResult]
    reason: str | None = None


def _name(discount: float, rarity: float | None, hours: float | None, hold: int) -> str:
    parts = [f"-{discount:g}%"]
    if rarity is not None:
        parts.append(f"редкость ≤{rarity:g}%")
    if hours is not None:
        parts.append(f"продажа <{hours:g}ч")
    parts.append(f"{hold}ч")
    return " · ".join(parts)


def _grid(collection_id: int | None) -> list[Strategy]:
    strategies: list[Strategy] = []
    for discount, rarity, hours, hold in itertools.product(
        DISCOUNT_STEPS, RARITY_STEPS, LIQUIDITY_STEPS, HOLD_STEPS
    ):
        strategies.append(
            Strategy(
                name=_name(discount, rarity, hours, hold),
                filters=Filters(
                    collection_id=collection_id,
                    min_discount_percent=discount,
                    max_rarity_percent=rarity,
                    max_hours_to_sell=hours,
                    # Any liquidity rule needs evidence behind it, otherwise it
                    # is satisfied by gifts we simply have not watched yet.
                    min_closed_listings=2 if hours is not None else None,
                ),
                hold_hours=hold,
                exit_at="floor",
            )
        )
    return strategies


def discover(data: Dataset, collection_id: int | None = None) -> Discovery:
    boundary = midpoint(data)
    candidates = _grid(collection_id)
    scored: list[tuple[float, BacktestResult]] = []
    for strategy in candidates:
        result = run_backtest(data, strategy, split_at=boundary)
        if result.status != "ok":
            continue
        # Ranked on the first half only. The second half is the exam, and an
        # exam you were allowed to study is not an exam.
        score = result.in_sample.median_profit_percent
        if score is None or result.in_sample.trades < 5:
            continue
        scored.append((score, result))

    if not scored:
        return Discovery(
            status="insufficient",
            tested=len(candidates),
            history_days=data.history_days,
            window_days=data.window_days,
            results=[],
            reason=(
                "Ни одна комбинация не набрала достаточно сделок. "
                f"История: {data.history_days:g} дней, кандидатов: {len(data.candidates)}. "
                "Нужно больше проходов парсеров."
            ),
        )

    scored.sort(key=lambda item: item[0], reverse=True)
    top = [result for _, result in scored[:MAX_RESULTS]]
    # Survivors first, so the honest ones are what a reader sees.
    top.sort(
        key=lambda result: (
            result.holds_up,
            result.out_of_sample.median_profit_percent or -999,
        ),
        reverse=True,
    )
    survivors = sum(1 for result in top if result.holds_up)
    return Discovery(
        status="ok",
        tested=len(candidates),
        history_days=data.history_days,
        window_days=data.window_days,
        results=top,
        reason=None
        if survivors
        else "Ни одна стратегия не подтвердилась на второй половине истории. Это результат, а не ошибка.",
    )
