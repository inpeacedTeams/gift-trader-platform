from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, Listing
from app.db.repositories.deals import DealRepository
from app.db.repositories.gifts import GiftRepository
from app.db.repositories.movers import MoversRepository
from app.db.repositories.trades import TradeRepository

MAX_COLLECTIONS = 25
MAX_DEALS = 15
MAX_MOVERS = 6


def ton(value: Decimal | None) -> str:
    if value is None:
        return "нет данных"
    number = Decimal(value).normalize()
    text = format(number, "f").rstrip("0").rstrip(".")
    return f"{text} TON"


async def market_context(session: AsyncSession) -> str:
    """A compact snapshot of everything we actually know.

    Kept small on purpose: the model answers better from a tight, factual
    briefing than from a dump of every row in the database.
    """
    lines: list[str] = []

    totals = (
        await session.execute(
            select(
                func.count(func.distinct(Gift.id)),
                func.count(Listing.id),
                func.min(Listing.price_ton),
            )
            .select_from(Gift)
            .join(Listing, (Listing.gift_id == Gift.id) & Listing.active.is_(True))
        )
    ).first()
    gifts_count, listings_count, floor = totals if totals else (0, 0, None)
    lines.append(
        f"РЫНОК: отслеживается подарков {gifts_count or 0}, "
        f"активных лотов {listings_count or 0}, самый дешёвый лот {ton(floor)}."
    )

    rows = (
        await session.execute(
            select(
                Collection.id,
                Collection.name,
                func.count(func.distinct(Gift.id)).label("models"),
                func.count(Listing.id).label("listings"),
                func.min(Listing.price_ton).label("floor"),
            )
            .join(Gift, Gift.collection_id == Collection.id)
            .outerjoin(Listing, (Listing.gift_id == Gift.id) & Listing.active.is_(True))
            .group_by(Collection.id)
            .order_by(func.count(Listing.id).desc())
            .limit(MAX_COLLECTIONS)
        )
    ).all()
    if rows:
        lines.append("\nКОЛЛЕКЦИИ (название, моделей, лотов, floor):")
        for row in rows:
            lines.append(
                f"- {row.name or 'без названия'}: моделей {row.models}, "
                f"лотов {row.listings}, floor {ton(row.floor)}"
            )

    deals = await DealRepository(session).deals(min_discount_percent=Decimal(5), limit=MAX_DEALS)
    if deals:
        lines.append("\nНЕДООЦЕНЁННЫЕ ЛОТЫ (ниже медианы своей модели):")
        for deal in deals:
            lines.append(
                f"- {deal['name'] or 'подарок'} {deal['model'] or ''}".rstrip()
                + f": {ton(deal['price_ton'])} против медианы {ton(deal['median_ton'])}, "
                + f"скидка {Decimal(deal['discount_percent']):.0f}%, площадка {deal['marketplace']}"
            )

    movers = await MoversRepository(session).movers(hours=24, limit=MAX_MOVERS)
    for label, key in (("РОСТ ЗА 24Ч", "gainers"), ("ПАДЕНИЕ ЗА 24Ч", "losers")):
        items = movers[key]
        if not items:
            continue
        lines.append(f"\n{label}:")
        for item in items:
            lines.append(
                f"- {item['name'] or 'подарок'} {item['model'] or ''}".rstrip()
                + f": {ton(item['previous_ton'])} -> {ton(item['floor_ton'])} "
                + f"({Decimal(item['change_percent']):+.1f}%)"
            )

    if len(lines) == 1:
        lines.append("\nДанных пока нет: рынок ещё не синхронизирован.")
    return "\n".join(lines)


async def gift_context(session: AsyncSession, gift_id: int) -> str | None:
    """Everything known about one gift, for the buy or skip verdict."""
    repository = GiftRepository(session)
    result = await repository.detail(gift_id)
    if result is None:
        return None
    gift, listings = result
    active = sorted([item for item in listings if item.active], key=lambda item: item.price_ton)
    floor = active[0].price_ton if active else None
    median = active[len(active) // 2].price_ton if active else None
    changes = await repository.changes([gift_id])
    deal = await repository.deal_percent(gift, floor)
    collection = await repository.collection_name(gift.collection_id)

    trades = TradeRepository(session)
    stats = await trades.stats(gift_id, days=30)
    recent = await trades.recent(gift_id, limit=5)

    lines = [
        f"ПОДАРОК: {gift.name or gift.canonical_id}",
        f"Коллекция: {collection or 'не определена'}",
        f"Модель: {gift.model or 'не определена'}",
        f"Номер: {gift.gift_number if gift.gift_number is not None else 'нет'}",
        f"Floor сейчас: {ton(floor)}",
        f"Медиана активных лотов: {ton(median)}",
        f"Активных лотов: {len(active)}",
        f"Площадки: {', '.join(sorted({item.marketplace for item in active})) or 'нет активных'}",
    ]
    change = changes.get(gift_id)
    lines.append(
        f"Изменение floor за 24ч: {Decimal(change):+.1f}%" if change is not None else
        "Изменение floor за 24ч: нет данных"
    )
    lines.append(
        f"Скидка к медиане своей модели: {Decimal(deal):.0f}%" if deal is not None else
        "Скидка к медиане своей модели: нет"
    )

    if stats["sales_count"]:
        lines.append(
            f"\nРЕАЛЬНЫЕ ПРОДАЖИ за {stats['window_days']} дней: сделок {stats['sales_count']}, "
            f"медиана {ton(stats['median_ton'])}, диапазон {ton(stats['lowest_ton'])} - {ton(stats['highest_ton'])}"
        )
        for trade in recent:
            lines.append(f"- продан за {ton(trade.price_ton)} ({trade.marketplace})")
    else:
        lines.append("\nРЕАЛЬНЫЕ ПРОДАЖИ: подтверждённых сделок в базе нет.")

    if active:
        lines.append("\nАКТИВНЫЕ ЛОТЫ:")
        for item in active[:8]:
            lines.append(f"- {ton(item.price_ton)} на {item.marketplace}")

    return "\n".join(lines)
