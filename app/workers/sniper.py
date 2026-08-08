"""Fast lane for mispriced listings.

The market crawl runs every few minutes and walks the whole book. That is
the wrong shape for sniping: by the time a full pass ends, a cheap lot has
been taken. This loop asks each marketplace for the cheapest page only, so
it is small enough to run every twenty seconds.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import AlertEvent, Gift, Listing, SniperHit, SniperWatch
from app.db.repositories.market_snapshot import MarketSnapshotRepository
from app.db.session import SessionLocal
from app.market.collector import collect
from app.market.registry import build_parsers
from app.market.models import SourceUnavailable

logger = logging.getLogger(__name__)
# One page per source. Cheap lots sort to the front, so this is where they land.
SNIPE_PAGES = 1


@dataclass(frozen=True)
class SnipeReport:
    scanned: int
    hits: int


def _ton(value: Decimal) -> str:
    """90.000000000 is noise. Print what a person would write."""
    return format(value.normalize(), "f")


def _matches(watch: SniperWatch, gift: Gift, listing: Listing, peer_median: Decimal | None) -> bool:
    if watch.marketplace and listing.marketplace != watch.marketplace:
        return False
    if watch.gift_name:
        name = (gift.name or "").lower()
        if watch.gift_name.lower() not in name:
            return False
    if watch.model and (gift.model or "").lower() != watch.model.lower():
        return False
    if watch.max_price_ton is not None and listing.price_ton > watch.max_price_ton:
        return False
    if watch.min_discount_percent is not None:
        if peer_median is None or peer_median <= 0:
            return False
        discount = (peer_median - listing.price_ton) / peer_median * Decimal(100)
        if discount < watch.min_discount_percent:
            return False
    return True


def _message(gift: Gift, listing: Listing, discount: Decimal | None) -> str:
    title = gift.name or f"Gift #{gift.id}"
    if gift.model:
        title = f"{title} · {gift.model}"
    lines = [
        "🎯 Снайпер",
        "",
        title,
        f"{_ton(listing.price_ton)} TON на {listing.marketplace}",
    ]
    if discount is not None and discount > 0:
        lines.append(f"На {discount:.0f}% ниже медианы модели")
    if listing.url:
        lines.extend(["", listing.url])
    return "\n".join(lines)


async def run_sniper(settings: Settings | None = None) -> SnipeReport:
    settings = settings or get_settings()
    async with SessionLocal() as session:
        watches = list(
            (await session.scalars(select(SniperWatch).where(SniperWatch.is_active.is_(True)))).all()
        )
    # Nobody is watching, so there is no reason to hit the marketplaces.
    if not watches:
        return SnipeReport(0, 0)

    parsers = build_parsers(settings=settings)
    for parser in parsers:
        # Shallow pass: only the cheapest page matters for sniping.
        if hasattr(parser, "max_pages"):
            parser.max_pages = SNIPE_PAGES
    try:
        result = await collect(parsers)
    except SourceUnavailable as exc:
        logger.info("sniper skipped", extra={"reason": exc.reason})
        return SnipeReport(0, 0)

    scanned = 0
    hits = 0
    async with SessionLocal() as session:
        repository = MarketSnapshotRepository(session)
        touched: set[int] = set()
        for snapshot in result.snapshots:
            persisted = await repository.persist(snapshot)
            scanned += persisted.listings
            touched |= persisted.gift_ids
        if not touched:
            return SnipeReport(scanned, 0)

        watches = list(
            (await session.scalars(select(SniperWatch).where(SniperWatch.is_active.is_(True)))).all()
        )
        rows = (
            await session.execute(
                select(Listing, Gift)
                .join(Gift, Gift.id == Listing.gift_id)
                .where(Listing.gift_id.in_(touched), Listing.active.is_(True))
                .order_by(Listing.price_ton.asc())
            )
        ).all()
        medians = await _peer_medians(session, touched)

        for listing, gift in rows:
            peer_median = medians.get((gift.collection_id, gift.model))
            for watch in watches:
                if not _matches(watch, gift, listing, peer_median):
                    continue
                claimed = await session.scalar(
                    insert(SniperHit)
                    .values(watch_id=watch.id, listing_id=listing.id, price_ton=listing.price_ton)
                    .on_conflict_do_nothing(constraint="uq_sniper_hit")
                    .returning(SniperHit.id)
                )
                # A conflict means we already told this user about this listing.
                if claimed is None:
                    continue
                discount = (
                    (peer_median - listing.price_ton) / peer_median * Decimal(100)
                    if peer_median
                    else None
                )
                session.add(
                    AlertEvent(
                        rule_id=None,
                        user_id=watch.user_id,
                        gift_id=gift.id,
                        message=_message(gift, listing, discount),
                        observed_value=listing.price_ton,
                    )
                )
                hits += 1
        await session.commit()
    logger.info("sniper pass complete", extra={"scanned": scanned, "hits": hits})
    return SnipeReport(scanned, hits)


async def _peer_medians(
    session: AsyncSession, gift_ids: set[int]
) -> dict[tuple[int | None, str | None], Decimal]:
    """Model medians for the collections we just touched.

    Scoped on purpose: aggregating every active listing on the market every
    twenty seconds is a lot of work for a handful of new lots.
    """
    collections = select(Gift.collection_id).where(
        Gift.id.in_(gift_ids), Gift.collection_id.is_not(None)
    )
    rows = (
        await session.execute(
            select(
                Gift.collection_id,
                Gift.model,
                func.percentile_cont(0.5).within_group(Listing.price_ton.asc()),
            )
            .join(Listing, (Listing.gift_id == Gift.id) & Listing.active.is_(True))
            .where(Gift.collection_id.in_(collections), Gift.model.is_not(None))
            .group_by(Gift.collection_id, Gift.model)
        )
    ).all()
    return {(collection_id, model): median for collection_id, model, median in rows if median}
