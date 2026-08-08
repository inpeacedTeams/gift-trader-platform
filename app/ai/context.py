"""Market context for the assistant.

Everything here is read from our own tables. The model is never given web
access and is told to refuse rather than guess, because an invented price is
worse than no answer in a trading tool.
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, Listing
from app.db.repositories.deals import DealRepository
from app.db.repositories.gifts import GiftRepository
from app.db.repositories.movers import MoversRepository
from app.db.repositories.trades import TradeRepository

MAX_COLLECTIONS = 12
MAX_DEALS = 10
MAX_MOVERS = 5


def ton(value: Decimal | None) -> str:
    if value is None:
        return "n/a"
    number = Decimal(value).normalize()
    return f"{number:f} TON"


async def market_overview(session: AsyncSession) -> str:
    """Top collections by depth, current discounts and 24h movement."""
    lines: list[str] = []

    rows = (
        await session.execute(
            select(
                Collection.name,
                func.count(func.distinct(Gift.id)).label("gifts"),
                func.min(Listing.price_ton).label("floor"),
                func.count(Listing.id).label("listings"),
            )
            .join(Gift, Gift.collection_id == Collection.id)
            .join(Listing, (Listing.gift_id == Gift.id) & Listing.active.is_(True))
            .group_by(Collection.id)
            .order_by(func.count(Listing.id).desc())
            .limit(MAX_COLLECTIONS)
        )
    ).all()
    if rows:
        lines.append("COLLECTIONS (name | models | floor | active listings):")
        for row in rows:
            lines.append(
                f"- {row.name or 'unnamed'} | {row.gifts} | {ton(row.floor)} | {row.listings}"
            )

    deals = await DealRepository(session).deals(min_discount_percent=Decimal(10), limit=MAX_DEALS)
    if deals:
        lines.append("")
        lines.append("UNDERPRICED LISTINGS (gift | model | price | model median | discount | market):")
        for deal in deals:
            lines.append(
                f"- [id {deal['gift_id']}] {deal['name'] or 'unnamed'} | {deal['model'] or 'n/a'} | "
                f"{ton(deal['price_ton'])} | {ton(deal['median_ton'])} | "
                f"{Decimal(deal['discount_percent']).quantize(Decimal('1'))}% | {deal['marketplace']}"
            )

    movers = await MoversRepository(session).movers(hours=24, limit=MAX_MOVERS)
    for label, items in (("GAINERS 24H", movers["gainers"]), ("LOSERS 24H", movers["losers"])):
        if not items:
            continue
        lines.append("")
        lines.append(f"{label} (gift | floor now | floor before | change):")
        for item in items:
            lines.append(
                f"- [id {item['gift_id']}] {item['name'] or 'unnamed'} | {ton(item['floor_ton'])} | "
                f"{ton(item['previous_ton'])} | {Decimal(item['change_percent']).quantize(Decimal('1.0'))}%"
            )

    if not lines:
        return "NO MARKET DATA STORED YET."
    return "\n".join(lines)


async def gift_context(session: AsyncSession, gift_id: int) -> str | None:
    """Everything known about one gift: listings, peers and real sales."""
    repository = GiftRepository(session)
    result = await repository.detail(gift_id)
    if result is None:
        return None
    gift, listings = result
    active = sorted([item for item in listings if item.active], key=lambda item: item.price_ton)
    floor = active[0].price_ton if active else None
    lines = [
        f"GIFT: {gift.name or 'unnamed'}",
        f"MODEL: {gift.model or 'unknown'}",
        f"COLLECTION: {await repository.collection_name(gift.collection_id) or 'unknown'}",
        f"FLOOR: {ton(floor)}",
        f"ACTIVE LISTINGS: {len(active)}",
    ]

    discount = await repository.deal_percent(gift, floor)
    if discount is not None:
        lines.append(f"DISCOUNT VS SAME MODEL MEDIAN: {Decimal(discount).quantize(Decimal('1'))}%")

    changes = await repository.changes([gift_id])
    if gift_id in changes:
        lines.append(f"FLOOR CHANGE 24H: {Decimal(changes[gift_id]).quantize(Decimal('1.0'))}%")

    if active:
        lines.append("")
        lines.append("LISTINGS (market | price):")
        for item in active[:8]:
            lines.append(f"- {item.marketplace} | {ton(item.price_ton)}")

    trades = TradeRepository(session)
    stats = await trades.stats(gift_id, days=30)
    if stats["sales_count"]:
        lines.append("")
        lines.append(
            f"CONFIRMED SALES 30D: {stats['sales_count']} | median {ton(stats['median_ton'])} | "
            f"range {ton(stats['lowest_ton'])} to {ton(stats['highest_ton'])}"
        )
        recent = await trades.recent(gift_id, limit=6)
        lines.append("RECENT SALES (price | market):")
        for trade in recent:
            lines.append(f"- {ton(trade.price_ton)} | {trade.marketplace}")
    else:
        lines.append("")
        lines.append("CONFIRMED SALES 30D: none stored")

    return "\n".join(lines)
