from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, Listing, PriceSnapshot

SORTS = ("recent", "floor_asc", "floor_desc", "depth", "change_desc", "change_asc")


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
        active_only: bool,
    ) -> Select:
        """Gift rows with market aggregates taken from currently active listings.

        Reading the aggregates here keeps the catalog to a single query and
        makes floor and depth sortable, which a per row snapshot lookup cannot do.
        """
        listing_join = (Listing.gift_id == Gift.id) & Listing.active.is_(True)
        if marketplace:
            listing_join = listing_join & (Listing.marketplace == marketplace)
        statement = (
            select(
                Gift,
                func.min(Listing.price_ton).label("floor_ton"),
                func.percentile_cont(0.5)
                .within_group(Listing.price_ton.asc())
                .label("median_ton"),
                func.count(Listing.id).label("listings_count"),
            )
            .outerjoin(Listing, listing_join)
            .group_by(Gift.id)
        )
        if active_only:
            statement = statement.where(Gift.is_active.is_(True))
        if collection_id is not None:
            statement = statement.where(Gift.collection_id == collection_id)
        if model:
            statement = statement.where(Gift.model == model)
        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(Gift.name.ilike(pattern), Gift.model.ilike(pattern), Gift.canonical_id.ilike(pattern))
            )
        if marketplace:
            statement = statement.having(func.count(Listing.id) > 0)
        return statement

    @staticmethod
    def _ordered(statement: Select, sort: str) -> Select:
        floor = func.min(Listing.price_ton)
        depth = func.count(Listing.id)
        if sort == "floor_asc":
            return statement.order_by(floor.asc().nullslast(), Gift.id.desc())
        if sort == "floor_desc":
            return statement.order_by(floor.desc().nullslast(), Gift.id.desc())
        if sort == "depth":
            return statement.order_by(depth.desc(), Gift.id.desc())
        return statement.order_by(Gift.id.desc())

    async def changes(self, gift_ids: list[int], hours: int = 24) -> dict[int, Decimal]:
        """Percent move of the floor over the window, batched for the whole page."""
        if not gift_ids:
            return {}
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        rows = (
            await self.session.execute(
                select(
                    PriceSnapshot.gift_id,
                    func.min(PriceSnapshot.observed_at).label("first_at"),
                    func.max(PriceSnapshot.observed_at).label("last_at"),
                )
                .where(PriceSnapshot.gift_id.in_(gift_ids), PriceSnapshot.observed_at >= since)
                .group_by(PriceSnapshot.gift_id)
            )
        ).all()
        if not rows:
            return {}
        bounds = {row.gift_id: (row.first_at, row.last_at) for row in rows}
        points = (
            await self.session.execute(
                select(PriceSnapshot.gift_id, PriceSnapshot.observed_at, PriceSnapshot.floor_ton).where(
                    PriceSnapshot.gift_id.in_(list(bounds)),
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
        sort: str = "recent",
        active_only: bool = True,
    ):
        base = self._base(
            search=search,
            marketplace=marketplace,
            collection_id=collection_id,
            model=model,
            active_only=active_only,
        )
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        rows = (
            await self.session.execute(
                self._ordered(base, sort).offset((page - 1) * page_size).limit(page_size)
            )
        ).all()
        changes = await self.changes([row[0].id for row in rows])
        if sort in ("change_desc", "change_asc"):
            rows = sorted(
                rows,
                key=lambda row: changes.get(row[0].id, Decimal(0)),
                reverse=sort == "change_desc",
            )
        return rows, int(total or 0), changes

    async def models(self, collection_id: int | None = None) -> list[str]:
        statement = select(Gift.model).where(Gift.model.is_not(None), Gift.is_active.is_(True))
        if collection_id is not None:
            statement = statement.where(Gift.collection_id == collection_id)
        rows = await self.session.scalars(statement.distinct().order_by(Gift.model.asc()))
        return [model for model in rows.all() if model]

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
