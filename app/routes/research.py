import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AssistantUnavailable, OpenRouterClient
from app.ai.limits import RateLimiter
from app.core.auth import current_user
from app.core.config import get_settings
from app.db.models import SavedStrategy, SniperWatch, StrategyRun, User
from app.db.session import get_session
from app.research.backtest import BacktestResult, Metrics, run_backtest
from app.research.dataset import Dataset, load_dataset
from app.research.discovery import discover
from app.research.propose import explain_result, propose_strategy
from app.research.strategy import Strategy

router = APIRouter(prefix="/research", tags=["research"])

_settings = get_settings()
ai_limiter = RateLimiter(_settings.ai_requests_per_hour)
MAX_SAVED = 40

# A grid search is dozens of backtests over identical rows. Reloading the
# history for each request would turn a cheap feature into an expensive one,
# and the data only changes when a crawl lands.
_CACHE_SECONDS = 120
_cache: dict[int, tuple[float, Dataset]] = {}


async def _dataset(session: AsyncSession, window_days: int) -> Dataset:
    cached = _cache.get(window_days)
    now = time.monotonic()
    if cached and now - cached[0] < _CACHE_SECONDS:
        return cached[1]
    data = await load_dataset(session, window_days=window_days)
    _cache[window_days] = (now, data)
    return data


class MetricsOut(BaseModel):
    trades: int
    wins: int
    win_rate: float | None = None
    median_profit_percent: float | None = None
    mean_profit_percent: float | None = None
    total_profit_ton: float = 0.0
    median_hold_hours: float | None = None
    best_percent: float | None = None
    worst_percent: float | None = None
    unresolved: int = 0


class TradeOut(BaseModel):
    gift_id: int
    gift_name: str | None = None
    marketplace: str
    entry_at: datetime
    entry_price: float
    exit_price: float
    profit_ton: float
    profit_percent: float
    # Did the listing actually leave the book inside the hold window. Evidence
    # it was sellable, never evidence of the price it sold at.
    sold: bool


class BacktestOut(BaseModel):
    status: str
    reason: str | None = None
    strategy: Strategy
    summary: str
    conditions: list[str]
    window_days: int
    history_days: float
    overall: MetricsOut
    in_sample: MetricsOut
    out_of_sample: MetricsOut
    holds_up: bool
    examples: list[TradeOut]


class DiscoveryOut(BaseModel):
    status: str
    reason: str | None = None
    tested: int
    window_days: int
    history_days: float
    results: list[BacktestOut]


class ProposeRequest(BaseModel):
    request: str = Field(min_length=3, max_length=400)
    window_days: int = Field(default=30, ge=1, le=90)


class ProposeOut(BaseModel):
    strategy: Strategy
    backtest: BacktestOut


class ExplainRequest(BaseModel):
    strategy: Strategy
    window_days: int = Field(default=30, ge=1, le=90)


class ExplainOut(BaseModel):
    explanation: str
    model: str
    backtest: BacktestOut


class SaveRequest(BaseModel):
    strategy: Strategy
    source: str = Field(default="manual", max_length=16)


class StrategyCard(BaseModel):
    id: int
    name: str
    source: str
    summary: str
    conditions: list[str]
    definition: Strategy
    created_at: datetime
    last_trades: int | None = None
    last_median_percent: float | None = None
    last_out_of_sample_percent: float | None = None
    last_holds_up: bool | None = None


class ArmOut(BaseModel):
    watch_id: int
    # Conditions the fast loop cannot enforce. Said out loud, because an
    # armed rule that is weaker than the tested one is a trap.
    dropped: list[str]


def _metrics(metrics: Metrics) -> MetricsOut:
    return MetricsOut(**metrics.as_dict())


def _out(result: BacktestResult) -> BacktestOut:
    return BacktestOut(
        status=result.status,
        reason=result.reason,
        strategy=result.strategy,
        summary=result.strategy.summary(),
        conditions=result.strategy.filters.describe(),
        window_days=result.window_days,
        history_days=result.history_days,
        overall=_metrics(result.overall),
        in_sample=_metrics(result.in_sample),
        out_of_sample=_metrics(result.out_of_sample),
        holds_up=result.holds_up,
        examples=[
            TradeOut(
                gift_id=trade.gift_id,
                gift_name=trade.gift_name,
                marketplace=trade.marketplace,
                entry_at=datetime.fromtimestamp(trade.entry_at, tz=timezone.utc),
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                profit_ton=trade.profit_ton,
                profit_percent=trade.profit_percent,
                sold=trade.sold,
            )
            for trade in result.examples
        ],
    )


def _client() -> OpenRouterClient:
    client = OpenRouterClient(get_settings())
    if not client.configured:
        raise HTTPException(503, "AI не настроен: задайте OPENROUTER_API_KEY")
    return client


def _quota(user: User) -> None:
    allowed, _ = ai_limiter.check(user.id)
    if not allowed:
        raise HTTPException(429, "Лимит AI-запросов на этот час исчерпан")


@router.post("/discover", response_model=DiscoveryOut)
async def discover_strategies(
    window_days: int = Query(default=30, ge=1, le=90),
    collection_id: int | None = Query(default=None),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    """Search the rule space and report what survived validation.

    No model is involved. This is arithmetic over stored listings and price
    snapshots, which is the only reason the numbers can be trusted.
    """
    data = await _dataset(session, window_days)
    found = discover(data, collection_id=collection_id)
    return DiscoveryOut(
        status=found.status,
        reason=found.reason,
        tested=found.tested,
        window_days=found.window_days,
        history_days=found.history_days,
        results=[_out(result) for result in found.results],
    )


@router.post("/backtest", response_model=BacktestOut)
async def backtest(
    body: ExplainRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    """Measure one rule set against stored history."""
    data = await _dataset(session, body.window_days)
    return _out(run_backtest(data, body.strategy))


@router.post("/propose", response_model=ProposeOut)
async def propose(
    body: ProposeRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    """Turn a request in words into a rule, then measure it ourselves.

    The model chooses the thresholds and nothing else. The performance figures
    that come back are the engine's.
    """
    client = _client()
    _quota(user)
    try:
        strategy = await propose_strategy(client, body.request)
    except AssistantUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    data = await _dataset(session, body.window_days)
    return ProposeOut(strategy=strategy, backtest=_out(run_backtest(data, strategy)))


@router.post("/explain", response_model=ExplainOut)
async def explain(
    body: ExplainRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    """Describe a measured result in words. The numbers are handed to it."""
    client = _client()
    _quota(user)
    data = await _dataset(session, body.window_days)
    result = run_backtest(data, body.strategy)
    try:
        text = await explain_result(client, result)
    except AssistantUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    return ExplainOut(explanation=text, model=client.model, backtest=_out(result))


@router.get("/strategies", response_model=list[StrategyCard])
async def strategies(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    rows = list(
        (
            await session.scalars(
                select(SavedStrategy)
                .where(SavedStrategy.user_id == user.id)
                .order_by(SavedStrategy.created_at.desc())
            )
        ).all()
    )
    latest: dict[int, StrategyRun] = {}
    if rows:
        runs = (
            await session.scalars(
                select(StrategyRun)
                .where(StrategyRun.strategy_id.in_([row.id for row in rows]))
                .order_by(StrategyRun.created_at.desc())
            )
        ).all()
        for run in runs:
            latest.setdefault(run.strategy_id, run)
    cards: list[StrategyCard] = []
    for row in rows:
        definition = Strategy.model_validate(row.definition)
        run = latest.get(row.id)
        cards.append(
            StrategyCard(
                id=row.id,
                name=row.name,
                source=row.source,
                summary=definition.summary(),
                conditions=definition.filters.describe(),
                definition=definition,
                created_at=row.created_at,
                last_trades=run.trades if run else None,
                last_median_percent=float(run.median_profit_percent)
                if run and run.median_profit_percent is not None
                else None,
                last_out_of_sample_percent=float(run.out_of_sample_percent)
                if run and run.out_of_sample_percent is not None
                else None,
                last_holds_up=run.holds_up if run else None,
            )
        )
    return cards


@router.post("/strategies", response_model=StrategyCard, status_code=201)
async def save_strategy(
    body: SaveRequest,
    window_days: int = Query(default=30, ge=1, le=90),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    """Keep a rule, and record the measurement it was kept on.

    The run is stored alongside so a claim can be checked later against the
    history that existed when it was made.
    """
    count = await session.scalar(
        select(func.count(SavedStrategy.id)).where(SavedStrategy.user_id == user.id)
    )
    if (count or 0) >= MAX_SAVED:
        raise HTTPException(422, f"Максимум {MAX_SAVED} сохранённых стратегий")
    saved = SavedStrategy(
        user_id=user.id,
        name=body.strategy.name,
        source=body.source if body.source in ("discovered", "ai", "manual") else "manual",
        definition=body.strategy.model_dump(),
    )
    session.add(saved)
    await session.flush()

    data = await _dataset(session, window_days)
    result = run_backtest(data, body.strategy)
    session.add(
        StrategyRun(
            strategy_id=saved.id,
            window_days=result.window_days,
            history_days=result.history_days,
            trades=result.overall.trades,
            median_profit_percent=result.overall.median_profit_percent,
            out_of_sample_percent=result.out_of_sample.median_profit_percent,
            holds_up=result.holds_up,
            metrics={
                "overall": result.overall.as_dict(),
                "in_sample": result.in_sample.as_dict(),
                "out_of_sample": result.out_of_sample.as_dict(),
                "status": result.status,
                "reason": result.reason,
            },
        )
    )
    await session.commit()
    await session.refresh(saved)
    return StrategyCard(
        id=saved.id,
        name=saved.name,
        source=saved.source,
        summary=body.strategy.summary(),
        conditions=body.strategy.filters.describe(),
        definition=body.strategy,
        created_at=saved.created_at,
        last_trades=result.overall.trades,
        last_median_percent=result.overall.median_profit_percent,
        last_out_of_sample_percent=result.out_of_sample.median_profit_percent,
        last_holds_up=result.holds_up,
    )


@router.delete("/strategies/{strategy_id}", status_code=204)
async def delete_strategy(
    strategy_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        delete(SavedStrategy).where(
            SavedStrategy.id == strategy_id, SavedStrategy.user_id == user.id
        )
    )
    await session.commit()


@router.post("/strategies/{strategy_id}/arm", response_model=ArmOut, status_code=201)
async def arm_strategy(
    strategy_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    """Turn a researched rule into a live sniper watch.

    The fast loop only understands price, discount, name, model and venue.
    Anything else in the strategy cannot be enforced live, so it is dropped
    and named in the response: an armed rule that is quietly looser than the
    tested one is worse than no rule at all.
    """
    saved = await session.scalar(
        select(SavedStrategy).where(
            SavedStrategy.id == strategy_id, SavedStrategy.user_id == user.id
        )
    )
    if saved is None:
        raise HTTPException(404, "Стратегия не найдена")
    strategy = Strategy.model_validate(saved.definition)
    rules = strategy.filters

    dropped: list[str] = []
    if rules.max_rarity_percent is not None:
        dropped.append(f"редкость ≤ {rules.max_rarity_percent:g}%")
    if rules.max_hours_to_sell is not None:
        dropped.append(f"время продажи < {rules.max_hours_to_sell:g} ч")
    if rules.min_closed_listings:
        dropped.append(f"история из {rules.min_closed_listings} закрытых лотов")
    if rules.min_price_ton:
        dropped.append(f"цена от {rules.min_price_ton:g} TON")
    if rules.collection_id is not None:
        dropped.append("фильтр по коллекции")
    if len(rules.marketplaces) > 1:
        dropped.append("несколько площадок сразу")

    if rules.max_price_ton is None and rules.min_discount_percent is None:
        raise HTTPException(
            422,
            "Снайпер понимает только цену и скидку. В этой стратегии нет ни того, ни другого.",
        )
    watch = SniperWatch(
        user_id=user.id,
        gift_name=None,
        model=None,
        max_price_ton=rules.max_price_ton,
        min_discount_percent=rules.min_discount_percent,
        marketplace=rules.marketplaces[0] if len(rules.marketplaces) == 1 else None,
    )
    session.add(watch)
    await session.commit()
    await session.refresh(watch)
    return ArmOut(watch_id=watch.id, dropped=dropped)
