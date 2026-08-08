"""Turns database rows into the only facts the model is allowed to use.

Everything here reads from our own tables. The assistant never browses the
web and never sees a price we did not collect ourselves, because a
hallucinated floor is worse than no answer at all.
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, Listing, PriceSnapshot, Trade
from app.db.repositories import GiftRepository, TradeRepository

MAX_COLLECTIONS = 12
MAX_GIFTS = 25


def _ton(value: Decimal | None) -> str:
    if value is None:
        return "n/a"
    number = Decimal(value).normalize()
    return f"{number:f} TON"


def _trait(name: str | None, percent: Decimal | None) -> str:
    """Name plus its published scarcity, or an honest admission of ignorance."""
    if not name:
        return "unresolved"
    if percent is None:
        return f"{name} (rarity unknown)"
    return f"{name} ({Decimal(percent).normalize():f}% of the collection)"


async def market_context(session: AsyncSession, *, limit: int = MAX_GIFTS) -> str:
    """A compact snapshot of the tracked market.

    Kept small on purpose: a short factual block beats a huge dump the model
    will skim, and it keeps token cost near zero.
    """
    lines: list[str] = []

    collections = (
        await session.execute(
            select(
                Collection.name,
                func.count(func.distinct(Gift.id)).label("gifts"),
                func.min(Listing.price_ton).label("floor"),
                func.count(Listing.id).label("listings"),
            )
            .join(Gift, Gift.collection_id == Collection.id)
            .outerjoin(Listing, (Listing.gift_id == Gift.id) & Listing.active.is_(True))
            .group_by(Collection.id)
            .order_by(func.count(Listing.id).desc())
            .limit(MAX_COLLECTIONS)
        )
    ).all()
    if collections:
        lines.append("COLLECTIONS (name | models | active listings | floor):")
        for row in collections:
            lines.append(
                f"- {row.name or 'unnamed'} | {row.gifts} | {row.listings} | {_ton(row.floor)}"
            )

    gifts = (
        await session.execute(
            select(
                Gift.id,
                Gift.name,
                Gift.model,
                Gift.rarity_tier,
                Collection.name.label("collection"),
                func.min(Listing.price_ton).label("floor"),
                func.percentile_cont(0.5)
                .within_group(Listing.price_ton.asc())
                .label("median"),
                func.count(Listing.id).label("depth"),
            )
            .join(Listing, (Listing.gift_id == Gift.id) & Listing.active.is_(True))
            .outerjoin(Collection, Collection.id == Gift.collection_id)
            .group_by(Gift.id, Collection.name)
            .order_by(func.count(Listing.id).desc())
            .limit(limit)
        )
    ).all()
    if gifts:
        lines.append("")
        lines.append("GIFTS (id | collection | model | rarity | floor | median | listings):")
        for row in gifts:
            lines.append(
                f"- #{row.id} | {row.collection or row.name or 'unknown'} | "
                f"{row.model or 'unknown model'} | {row.rarity_tier or 'rarity unknown'} | "
                f"{_ton(row.floor)} | {_ton(row.median)} | {row.depth}"
            )

    trades = (
        await session.execute(
            select(func.count(Trade.id), func.max(Trade.traded_at))
        )
    ).first()
    snapshots = await session.scalar(select(func.max(PriceSnapshot.observed_at)))
    lines.append("")
    lines.append(
        f"DATA FRESHNESS: last price snapshot {snapshots or 'never'}, "
        f"{trades[0] if trades else 0} recorded sales, last sale {trades[1] if trades else 'never'}."
    )
    return "\n".join(lines).strip()


async def gift_context(session: AsyncSession, gift_id: int) -> str | None:
    """Everything known about one gift: traits, listings, movement, real sales."""
    repository = GiftRepository(session)
    result = await repository.detail(gift_id)
    if result is None:
        return None
    gift, listings = result
    active = sorted([item for item in listings if item.active], key=lambda item: item.price_ton)
    prices = [item.price_ton for item in active]
    floor = prices[0] if prices else None
    changes = await repository.changes([gift_id])
    collection = await repository.collection_name(gift.collection_id)
    deal = await repository.deal_percent(gift, floor)
    stats = await TradeRepository(session).stats(gift_id)

    lines = [
        f"GIFT: {gift.name or gift.canonical_id}",
        f"Collection: {collection or 'unresolved'}",
        f"Model: {_trait(gift.model, gift.model_rarity)}",
        f"Backdrop: {_trait(gift.backdrop, gift.backdrop_rarity)}",
        f"Symbol: {_trait(gift.symbol, gift.symbol_rarity)}",
        f"Rarity tier: {gift.rarity_tier or 'unknown, no source published a rarity'}",
        f"Floor: {_ton(floor)}",
        f"Median of active listings: {_ton(prices[len(prices) // 2] if prices else None)}",
        f"Active listings: {len(active)}",
    ]
    change = changes.get(gift_id)
    if change is not None:
        lines.append(f"Floor change over 24h: {Decimal(change):.2f}%")
    if deal is not None:
        lines.append(
            f"Discount against peers of the same model and rarity tier: {Decimal(deal):.2f}%"
        )
    if active:
        lines.append("Cheapest listings:")
        for item in active[:5]:
            lines.append(f"- {item.marketplace}: {_ton(item.price_ton)}")
    if stats["sales_count"]:
        lines.append(
            f"Confirmed sales in {stats['window_days']}d: {stats['sales_count']}, "
            f"median {_ton(stats['median_ton'])}, "
            f"range {_ton(stats['lowest_ton'])} to {_ton(stats['highest_ton'])}"
        )
    else:
        lines.append("Confirmed sales: none recorded, valuation rests on asking prices only.")
    return "\n".join(lines)
