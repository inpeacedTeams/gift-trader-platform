from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Numeric, Select, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, Listing, PriceSnapshot

SORTS = ("recent", "floor_asc", "floor_desc", "depth", "change_desc", "change_asc", "deal_desc")
# A discount is only meaningful once the peer group has real depth.
MIN_PEER_LISTINGS = 3
# The traits the catalog can filter and break down by.
TRAIT_COLUMNS = (
    ("model", Gift.model, Gift.model_rarity),
    ("backdrop", Gift.backdrop, Gift.backdrop_rarity),
    ("symbol", Gift.symbol, Gift.symbol_rarity),
)


def _peer_medians():
    """Median active price for every collection, model and rarity tier.

    This is the reference a gift is judged against. Rarity belongs in the key:
    a Plush Pepe with a one in five hundred backdrop is not overpriced just
    because the plain ones are cheaper, and the old model only grouping made
    exactly that mistake. Gifts with no rarity data group together under a
    NULL tier, which is why the join is NULL safe.
    """
    return (
        select(
            Gift.collection_id.label("collection_id"),
            Gift.model.label("model"),
            Gift.rarity_tier.label("rarity_tier"),
            func.percentile_cont(0.5)
            .within_group(Listing.price_ton.asc())
            .label("peer_median"),
            func.count(Listing.id).label("peer_count"),
        )
        .join(Listing, and_(Listing.gift_id == Gift.id, Listing.active.is_(True)))
        .where(Gift.model.is_not(None), Gift.collection_id.is_not(None))
        .group_by(Gift.collection_id, Gift.model, Gift.rarity_tier)
        .subquery()
    )


def _peer_join(peers, tier=None):
    """Match a gift to its peer group. NULL tiers must match each other."""
    return and_(
        peers.c.collection_id == Gift.collection_id,
        peers.c.model == Gift.model,
        peers.c.rarity_tier.is_not_distinct_from(Gift.rarity_tier if tier is None else tier),
    )


class GiftRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _base(
        self,
        *,
        search: str | None,
        marketplace: str | None,
        collection_id: int | None,
        model: str | None,
        backdrop: str | None,
        symbol: str | None,
        rarity_tier: str | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        deals_only: bool,
        active_only: bool,
    ) -> tuple[Select, object]:
        """Gift rows with market aggregates taken from currently active listings.

        Reading the aggregates here keeps the catalog to a single query and
        makes floor, depth and discount sortable, which a per row lookup cannot do.
        """
        listing_join = (Listing.gift_id == Gift.id) & Listing.active.is_(True)
        if marketplace:
            listing_join = listing_join & (Listing.marketplace == marketplace)
        peers = _peer_medians()
        floor = func.min(Listing.price_ton)
        deal = case(
            (
                and_(
                    peers.c.peer_count >= MIN_PEER_LISTINGS,
                    peers.c.peer_median > 0,
                    floor < peers.c.peer_median,
                ),
                cast(
                    (peers.c.peer_median - floor) / peers.c.peer_median * 100,
                    Numeric(6, 2),
                ),
            ),
            else_=None,
        ).label("deal_percent")
        statement = (
            select(
                Gift,
                floor.label("floor_ton"),
                func.percentile_cont(0.5)
                .within_group(Listing.price_ton.asc())
                .label("median_ton"),
                func.count(Listing.id).label("listings_count"),
                deal,
            )
            .outerjoin(Listing, listing_join)
            .outerjoin(peers, _peer_join(peers))
            .group_by(Gift.id, peers.c.peer_median, peers.c.peer_count)
        )
        if active_only:
            statement = statement.where(Gift.is_active.is_(True))
        if collection_id is not None:
            statement = statement.where(Gift.collection_id == collection_id)
        if model:
            statement = statement.where(Gift.model == model)
        if backdrop:
            statement = statement.where(Gift.backdrop == backdrop)
        if symbol:
            statement = statement.where(Gift.symbol == symbol)
        if rarity_tier:
            statement = statement.where(Gift.rarity_tier == rarity_tier)
        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(
                    Gift.name.ilike(pattern),
                    Gift.model.ilike(pattern),
                    Gift.backdrop.ilike(pattern),
                    Gift.symbol.ilike(pattern),
                    Gift.canonical_id.ilike(pattern),
                )
            )
        if marketplace:
            statement = statement.having(func.count(Listing.id) > 0)
        if min_price is not None:
            statement = statement.having(floor >= min_price)
        if max_price is not None:
            statement = statement.having(floor <= max_price)
        if deals_only:
            statement = statement.having(
                and_(
                    peers.c.peer_count >= MIN_PEER_LISTINGS,
                    peers.c.peer_median > 0,
                    floor < peers.c.peer_median,
                )
            )
        return statement, deal

    @staticmethod
    def _ordered(statement: Select, sort: str, deal) -> Select:
        floor = func.min(Listing.price_ton)
        depth = func.count(Listing.id)
        if sort == "floor_asc":
            return statement.order_by(floor.asc().nullslast(), Gift.id.desc())
        if sort == "floor_desc":
            return statement.order_by(floor.desc().nullslast(), Gift.id.desc())
        if sort == "depth":
            return statement.order_by(depth.desc(), Gift.id.desc())
        if sort == "deal_desc":
            return statement.order_by(deal.desc().nullslast(), Gift.id.desc())
        return statement.order_by(Gift.id.desc())

    async def best_venues(self, gift_ids: list[int]) -> dict[int, str]:
        """Marketplace holding the cheapest active listing for each gift."""
        if not gift_ids:
            return {}
        rows = (
            await self.session.execute(
                select(Listing.gift_id, Listing.marketplace)
                .where(Listing.gift_id.in_(gift_ids), Listing.active.is_(True))
                .distinct(Listing.gift_id)
                .order_by(Listing.gift_id, Listing.price_ton.asc())
            )
        ).all()
        return {gift_id: marketplace for gift_id, marketplace in rows}

    async def changes(self, gift_ids: list[int], hours: int = 24) -> dict[int, Decimal]:
        """Percent move of the floor over the window, batched for the whole page."""
        if not gift_ids:
            return {}
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        points = (
            await self.session.execute(
                select(PriceSnapshot.gift_id, PriceSnapshot.observed_at, PriceSnapshot.floor_ton).where(
                    PriceSnapshot.gift_id.in_(gift_ids),
                    PriceSnapshot.observed_at >= since,
                    PriceSnapshot.floor_ton.is_not(None),
                )
            )
        ).all()
        first: dict[int, tuple[datetime, Decimal]] = {}
        last: dict[int, tuple[datetime, Decimal]] = {}
        for gift_id, observed_at, floor in points:
            if gift_id not in first or observed_at < first[gift_id][0]:
                first[gift_id] = (observed_at, floor)
            if gift_id not in last or observed_at > last[gift_id][0]:
                last[gift_id] = (observed_at, floor)
        changes: dict[int, Decimal] = {}
        for gift_id, (_, opening) in first.items():
            closing = last[gift_id][1]
            if opening and opening > 0 and closing != opening:
                changes[gift_id] = (closing - opening) / opening * Decimal(100)
        return changes

    async def page(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        marketplace: str | None = None,
        collection_id: int | None = None,
        model: str | None = None,
        backdrop: str | None = None,
        symbol: str | None = None,
        rarity_tier: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        deals_only: bool = False,
        sort: str = "recent",
        active_only: bool = True,
    ):
        base, deal = self._base(
            search=search,
            marketplace=marketplace,
            collection_id=collection_id,
            model=model,
            backdrop=backdrop,
            symbol=symbol,
            rarity_tier=rarity_tier,
            min_price=min_price,
            max_price=max_price,
            deals_only=deals_only,
            active_only=active_only,
        )
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        rows = (
            await self.session.execute(
                self._ordered(base, sort, deal).offset((page - 1) * page_size).limit(page_size)
            )
        ).all()
        gift_ids = [row[0].id for row in rows]
        changes = await self.changes(gift_ids)
        venues = await self.best_venues(gift_ids)
        if sort in ("change_desc", "change_asc"):
            rows = sorted(
                rows,
                key=lambda row: changes.get(row[0].id, Decimal(0)),
                reverse=sort == "change_desc",
            )
        return rows, int(total or 0), changes, venues

    async def models(self, collection_id: int | None = None) -> list[str]:
        statement = select(Gift.model).where(Gift.model.is_not(None), Gift.is_active.is_(True))
        if collection_id is not None:
            statement = statement.where(Gift.collection_id == collection_id)
        rows = await self.session.scalars(statement.distinct().order_by(Gift.model.asc()))
        return [model for model in rows.all() if model]

    async def attributes(self, collection_id: int | None = None) -> dict[str, list[dict]]:
        """Every trait we track, with how scarce it is and what it costs.

        Rarity says how few exist, the floor says what the market pays. A
        flipper needs both: a 0.2% backdrop trading at the collection floor is
        the whole trade, and neither number alone reveals it.
        """
        groups: dict[str, list[dict]] = {}
        for slot, column, rarity_column in TRAIT_COLUMNS:
            statement = (
                select(
                    column.label("value"),
                    func.min(rarity_column).label("rarity_percent"),
                    func.count(func.distinct(Gift.id)).label("gift_count"),
                    func.count(Listing.id).label("listings_count"),
                    func.min(Listing.price_ton).label("floor_ton"),
                )
                .outerjoin(Listing, and_(Listing.gift_id == Gift.id, Listing.active.is_(True)))
                .where(column.is_not(None), Gift.is_active.is_(True))
                .group_by(column)
                .order_by(column.asc())
            )
            if collection_id is not None:
                statement = statement.where(Gift.collection_id == collection_id)
            rows = (await self.session.execute(statement)).all()
            groups[slot] = [
                {
                    "value": row.value,
                    "rarity_percent": row.rarity_percent,
                    "gift_count": int(row.gift_count or 0),
                    "listings_count": int(row.listings_count or 0),
                    "floor_ton": row.floor_ton,
                }
                for row in rows
            ]
        return groups

    async def collection_name(self, collection_id: int | None) -> str | None:
        if collection_id is None:
            return None
        return await self.session.scalar(select(Collection.name).where(Collection.id == collection_id))

    async def detail(self, gift_id: int):
        gift = await self.session.get(Gift, gift_id)
        if gift is None:
            return None
        listings = list(
            (
                await self.session.scalars(
                    select(Listing).where(Listing.gift_id == gift_id).order_by(Listing.price_ton.asc())
                )
            ).all()
        )
        return gift, listings

    async def deal_percent(self, gift: Gift, floor: Decimal | None) -> Decimal | None:
        """Discount of one gift against its peer group, for the detail page."""
        if floor is None or gift.model is None or gift.collection_id is None:
            return None
        peers = _peer_medians()
        row = (
            await self.session.execute(
                select(peers.c.peer_median, peers.c.peer_count).where(
                    peers.c.collection_id == gift.collection_id,
                    peers.c.model == gift.model,
                    peers.c.rarity_tier.is_not_distinct_from(gift.rarity_tier),
                )
            )
        ).first()
        if row is None:
            return None
        median, count = row
        if count < MIN_PEER_LISTINGS or not median or median <= 0 or floor >= median:
            return None
        return (Decimal(median) - floor) / Decimal(median) * Decimal(100)

    async def latest_stats(self, gift_id: int):
        return list(
            (
                await self.session.scalars(
                    select(PriceSnapshot)
                    .where(PriceSnapshot.gift_id == gift_id)
                    .order_by(PriceSnapshot.observed_at.desc())
                    .limit(100)
                )
            ).all()
        )
