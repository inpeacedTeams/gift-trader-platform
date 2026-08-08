"""Turns stored market rows into prompt context.

The assistant is only allowed to reason over what we actually collected.
Everything here reads the database; nothing is inferred or fetched live,
so an answer can always be traced back to a row a user can open.
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, Listing
from app.db.repositories.deals import DealRepository
from app.db.repositories.gifts import GiftRepository
from app.db.repositories.movers import MoversRepository
from app.db.repositories.trades import TradeRepository

MAX_ROWS = 12


def ton(value: Decimal | None) -> str:
    if value is None:
        return "n/a"
    number = Decimal(value).normalize()
    return f"{number:f} TON"


async def market_overview(session: AsyncSession) -> str:
    """Top collections by live depth, so the model knows what exists."""
    rows = (
        await session.execute(
            select(
                Collection.name,
                func.count(Listing.id).label("listings"),
                func.min(Listing.price_ton).label("floor"),
            )
            .join(Gift, Gift.collection_id == Collection.id)
            .join(Listing, (Listing.gift_id == Gift.id) & Listing.active.is_(True))
            .group_by(Collection.id)
            .order_by(func.count(Listing.id).desc())
            .limit(MAX_ROWS)
        )
    ).all()
    if not rows:
        return "No collections tracked yet."
    lines = [
        f"- {row.name or 'unnamed'}: floor {ton(row.floor)}, {row.listings} active listings"
        for row in rows
    ]
    return "Tracked collections:\n" + "\n".join(lines)


async def deals_context(session: AsyncSession) -> str:
    rows = await DealRepository(session).deals(min_discount_percent=Decimal(8), limit=MAX_ROWS)
    if not rows:
        return "No listing is currently below its model median."
    lines = [
        f"- {row['name'] or 'gift'} {row['model'] or ''} #{row['gift_id']}: "
        f"{ton(row['price_ton'])} on {row['marketplace']}, "
        f"model median {ton(row['median_ton'])}, "
        f"{Decimal(row['discount_percent']):.0f}% below peers"
        for row in rows
    ]
    return "Underpriced listings:\n" + "\n".join(lines)


async def movers_context(session: AsyncSession) -> str:
    result = await MoversRepository(session).movers(hours=24, limit=5)
    if not result["gainers"] and not result["losers"]:
        return "No price movement recorded in the last 24 hours."

    def render(items: list[dict]) -> list[str]:
        return [
            f"- {item['name'] or 'gift'} #{item['gift_id']}: {ton(item['floor_ton'])} "
            f"({Decimal(item['change_percent']):+.1f}% in 24h)"
            for item in items
        ]

    blocks = []
    if result["gainers"]:
        blocks.append("Biggest 24h gainers:\n" + "\n".join(render(result["gainers"])))
    if result["losers"]:
        blocks.append("Biggest 24h losers:\n" + "\n".join(render(result["losers"])))
    return "\n\n".join(blocks)


async def gift_context(session: AsyncSession, gift_id: int) -> str | None:
    """Everything known about one gift: asks, sales and peer position."""
    repository = GiftRepository(session)
    detail = await repository.detail(gift_id)
    if detail is None:
        return None
    gift, listings = detail
    active = sorted([item for item in listings if item.active], key=lambda item: item.price_ton)
    floor = active[0].price_ton if active else None
    collection = await repository.collection_name(gift.collection_id)
    changes = await repository.changes([gift_id])
    deal_percent = await repository.deal_percent(gift, floor)
    stats = await TradeRepository(session).stats(gift_id, days=30)

    lines = [
        f"Gift: {gift.name or gift.canonical_id}",
        f"Collection: {collection or 'unresolved'}",
        f"Model: {gift.model or 'unresolved'}",
        f"Current floor: {ton(floor)}",
        f"Active listings: {len(active)}",
    ]
    if gift_id in changes:
        lines.append(f"24h floor change: {Decimal(changes[gift_id]):+.1f}%")
    if deal_percent is not None:
        lines.append(f"Below its model median by {Decimal(deal_percent):.0f}%")
    if stats["sales_count"]:
        lines.append(
            f"Confirmed sales in 30d: {stats['sales_count']}, "
            f"median paid {ton(stats['median_ton'])}, "
            f"range {ton(stats['lowest_ton'])} to {ton(stats['highest_ton'])}"
        )
    else:
        lines.append("Confirmed sales in 30d: none recorded")
    if active:
        venues = ", ".join(
            f"{item.marketplace} {ton(item.price_ton)}" for item in active[:6]
        )
        lines.append(f"Cheapest listings by venue: {venues}")
    return "\n".join(lines)


async def chat_context(session: AsyncSession) -> str:
    """Whole-market snapshot handed to the chat assistant."""
    blocks = [
        await market_overview(session),
        await deals_context(session),
        await movers_context(session),
    ]
    return "\n\n".join(blocks)
