"""Loads the history a backtest runs on, once.

A grid search evaluates dozens of rule sets. Querying per rule set would
mean dozens of full table scans, so everything the engine needs is pulled
in four queries and replayed in memory.

The important work here is not loading, it is refusing to leak the future
into the past. Every feature attached to a candidate entry is computed from
rows whose timestamp is at or before the moment that listing appeared.
"""

import bisect
from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from statistics import median

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Gift, Listing, PriceSnapshot

# Sanity bounds. A window longer than the database is pointless, and a
# candidate set larger than this is a sign the filters were forgotten.
MAX_WINDOW_DAYS = 90
MAX_CANDIDATES = 60_000


def _epoch(moment: datetime) -> float:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp()


@dataclass(frozen=True)
class Candidate:
    """A listing as it looked the moment it appeared on the book."""

    listing_id: int
    gift_id: int
    gift_name: str | None
    collection_id: int | None
    model: str | None
    rarity_tier: str | None
    marketplace: str
    entry_at: float
    entry_price: float
    # The gift's prevailing price when this lot appeared. Without it there is
    # nothing to call the listing cheap against.
    reference_price: float
    discount_percent: float
    rarity_percent: float | None
    # Liquidity as known at entry_at, not as it turned out later.
    prior_closed: int
    prior_median_hours: float | None
    closed_at: float | None


@dataclass
class Series:
    """A gift's observed price over time, ordered."""

    times: list[float] = field(default_factory=list)
    floor: list[float] = field(default_factory=list)
    median: list[float] = field(default_factory=list)

    def at(self, when: float, column: str) -> float | None:
        """Last observation at or before `when`. None before the series starts."""
        index = bisect_right(self.times, when) - 1
        if index < 0:
            return None
        values = self.floor if column == "floor" else self.median
        return values[index]

    @property
    def last(self) -> float | None:
        return self.times[-1] if self.times else None


@dataclass
class Dataset:
    candidates: list[Candidate]
    series: dict[int, Series]
    window_days: int
    # Real coverage, which is usually shorter than the requested window on a
    # database that has not been running long.
    history_days: float
    first_at: float | None
    last_at: float | None

    def price_at(self, gift_id: int, when: float, column: str) -> float | None:
        series = self.series.get(gift_id)
        return series.at(when, column) if series else None

    def has_data_after(self, gift_id: int, when: float) -> bool:
        """Is there any observation after `when`.

        An exit that falls past the end of our history is not a loss and not
        a win: the trade never resolved, and counting it either way would be
        a lie about the sample.
        """
        series = self.series.get(gift_id)
        return bool(series and series.last is not None and series.last >= when)


async def load_dataset(session: AsyncSession, window_days: int = 30) -> Dataset:
    window_days = max(1, min(window_days, MAX_WINDOW_DAYS))
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    since_epoch = _epoch(since)

    gifts = {
        row.id: row
        for row in (
            await session.execute(
                select(
                    Gift.id,
                    Gift.name,
                    Gift.collection_id,
                    Gift.model,
                    Gift.rarity_tier,
                    Gift.model_rarity,
                    Gift.backdrop_rarity,
                    Gift.symbol_rarity,
                )
            )
        ).all()
    }

    series: dict[int, Series] = {}
    snapshots = (
        await session.execute(
            select(
                PriceSnapshot.gift_id,
                PriceSnapshot.observed_at,
                PriceSnapshot.floor_ton,
                PriceSnapshot.median_ton,
            )
            .where(PriceSnapshot.observed_at >= since)
            .order_by(PriceSnapshot.gift_id, PriceSnapshot.observed_at)
        )
    ).all()
    for gift_id, observed_at, floor_ton, median_ton in snapshots:
        if floor_ton is None:
            continue
        entry = series.setdefault(gift_id, Series())
        moment = _epoch(observed_at)
        floor_value = float(floor_ton)
        median_value = float(median_ton) if median_ton is not None else floor_value
        # Several venues report the same gift in one pass. Keep the cheapest,
        # which is the price a buyer would actually have paid.
        if entry.times and entry.times[-1] == moment:
            entry.floor[-1] = min(entry.floor[-1], floor_value)
            entry.median[-1] = min(entry.median[-1], median_value)
            continue
        entry.times.append(moment)
        entry.floor.append(floor_value)
        entry.median.append(median_value)

    listings = (
        await session.execute(
            select(
                Listing.id,
                Listing.gift_id,
                Listing.marketplace,
                Listing.price_ton,
                Listing.first_seen_at,
                Listing.closed_at,
            )
            .where(Listing.first_seen_at >= since)
            .order_by(Listing.first_seen_at)
            .limit(MAX_CANDIDATES)
        )
    ).all()

    # Closures per gift, ordered, so "how did this gift behave before now"
    # can be answered without looking at anything after the entry.
    closures: dict[int, list[tuple[float, float]]] = {}
    for _, gift_id, _, _, first_seen_at, closed_at in listings:
        if closed_at is None:
            continue
        lifetime = (_epoch(closed_at) - _epoch(first_seen_at)) / 3600.0
        if lifetime <= 0:
            continue
        closures.setdefault(gift_id, []).append((_epoch(closed_at), lifetime))
    for values in closures.values():
        values.sort()

    candidates: list[Candidate] = []
    for listing_id, gift_id, marketplace, price_ton, first_seen_at, closed_at in listings:
        gift = gifts.get(gift_id)
        if gift is None or price_ton is None:
            continue
        entry_at = _epoch(first_seen_at)
        price = float(price_ton)
        if price <= 0:
            continue
        reference = series.get(gift_id).at(entry_at, "median") if gift_id in series else None
        # No prior observation means no basis to call this cheap or dear. The
        # listing is skipped rather than compared against itself.
        if reference is None or reference <= 0:
            continue
        prior_closed, prior_hours = _prior_liquidity(closures.get(gift_id), entry_at)
        rarity = _rarest(gift.model_rarity, gift.backdrop_rarity, gift.symbol_rarity)
        candidates.append(
            Candidate(
                listing_id=listing_id,
                gift_id=gift_id,
                gift_name=gift.name,
                collection_id=gift.collection_id,
                model=gift.model,
                rarity_tier=gift.rarity_tier,
                marketplace=marketplace,
                entry_at=entry_at,
                entry_price=price,
                reference_price=reference,
                discount_percent=(reference - price) / reference * 100.0,
                rarity_percent=rarity,
                prior_closed=prior_closed,
                prior_median_hours=prior_hours,
                closed_at=_epoch(closed_at) if closed_at else None,
            )
        )

    times = [moment for entry in series.values() for moment in entry.times]
    first_at = min(times) if times else None
    last_at = max(times) if times else None
    history_days = (last_at - first_at) / 86400.0 if first_at and last_at else 0.0
    return Dataset(
        candidates=candidates,
        series=series,
        window_days=window_days,
        history_days=round(max(history_days, 0.0), 2),
        first_at=first_at or since_epoch,
        last_at=last_at,
    )


def _prior_liquidity(
    closures: list[tuple[float, float]] | None, entry_at: float
) -> tuple[int, float | None]:
    """How this gift had been selling before this listing appeared.

    Using the whole window here would be the classic backtest fraud: the
    strategy would be picking gifts that turned out to be liquid, which is
    knowledge nobody had at the time of the buy.
    """
    if not closures:
        return 0, None
    cut = bisect.bisect_left(closures, (entry_at,))
    earlier = closures[:cut]
    if not earlier:
        return 0, None
    return len(earlier), round(median(lifetime for _, lifetime in earlier), 2)


def _rarest(*percents) -> float | None:
    known = [float(value) for value in percents if value is not None and float(value) > 0]
    return min(known) if known else None
