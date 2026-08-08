from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, Listing, Position
from app.market.economics import DEFAULT_GAS_TON, net_proceeds, sell_fee_percent

TON = Decimal("0.001")
CENT = Decimal("0.01")
HOUR = Decimal(3600)


class PositionRepository:
    """Open lots valued at what selling them today would actually pay.

    Marking a position at the floor is a lie by omission: the venue keeps a
    cut and the gas is already spent. Every figure here is net of both, and a
    gift with no live listing is reported as unvalued rather than carried at
    a stale price.
    """

    def __init__(self, session: AsyncSession, gas_ton: Decimal = DEFAULT_GAS_TON):
        self.session = session
        self.gas_ton = gas_ton

    async def _floors(self, gift_ids: list[int]) -> dict[int, tuple[Decimal, str]]:
        if not gift_ids:
            return {}
        rows = (
            await self.session.execute(
                select(Listing.gift_id, Listing.price_ton, Listing.marketplace)
                .where(Listing.gift_id.in_(gift_ids), Listing.active.is_(True))
                .order_by(Listing.gift_id, Listing.price_ton.asc())
            )
        ).all()
        floors: dict[int, tuple[Decimal, str]] = {}
        for gift_id, price, marketplace in rows:
            # Price ordered, so the first row per gift is its floor.
            floors.setdefault(gift_id, (price, marketplace))
        return floors

    async def _gifts(self, gift_ids: list[int]) -> dict[int, tuple]:
        if not gift_ids:
            return {}
        rows = (
            await self.session.execute(
                select(
                    Gift.id,
                    Gift.name,
                    Gift.model,
                    Gift.gift_number,
                    Gift.image_url,
                    Gift.rarity_tier,
                    Collection.name.label("collection_name"),
                )
                .outerjoin(Collection, Collection.id == Gift.collection_id)
                .where(Gift.id.in_(gift_ids))
            )
        ).all()
        return {row.id: row for row in rows}

    def _exit_venue(self, position: Position, floor_venue: str | None) -> str | None:
        """Where the exit would happen: the stated plan, else where it was
        bought, else wherever the gift currently trades."""
        return position.sell_marketplace or position.buy_marketplace or floor_venue

    def _card(self, position: Position, gift, floor: tuple[Decimal, str] | None) -> dict:
        now = datetime.now(timezone.utc)
        opened = position.opened_at or position.created_at
        until = position.closed_at or now
        held_hours = Decimal((until - opened).total_seconds()) / HOUR if opened else Decimal(0)
        # Gas was paid on the way in, so it belongs in the cost basis.
        cost = position.buy_price_ton + self.gas_ton
        floor_price, floor_venue = floor if floor else (None, None)
        venue = self._exit_venue(position, floor_venue)

        if position.closed_at and position.sell_price_ton is not None:
            proceeds = net_proceeds(position.sell_marketplace or venue, position.sell_price_ton)
            valued = True
        elif floor_price is not None:
            proceeds = net_proceeds(venue, floor_price)
            valued = True
        else:
            proceeds = None
            valued = False

        profit = None if proceeds is None else proceeds - cost
        percent = (
            None
            if profit is None or cost <= 0
            else (profit / cost * Decimal(100)).quantize(CENT, rounding=ROUND_HALF_UP)
        )
        return {
            "id": position.id,
            "gift_id": position.gift_id,
            "name": getattr(gift, "name", None),
            "model": getattr(gift, "model", None),
            "gift_number": getattr(gift, "gift_number", None),
            "image_url": getattr(gift, "image_url", None),
            "rarity_tier": getattr(gift, "rarity_tier", None),
            "collection_name": getattr(gift, "collection_name", None),
            "buy_price_ton": position.buy_price_ton,
            "buy_marketplace": position.buy_marketplace,
            "opened_at": opened,
            "sell_price_ton": position.sell_price_ton,
            "sell_marketplace": position.sell_marketplace,
            "closed_at": position.closed_at,
            "note": position.note,
            "is_open": position.closed_at is None,
            "days_held": int(held_hours / 24) if held_hours > 0 else 0,
            "cost_ton": cost.quantize(TON, rounding=ROUND_HALF_UP),
            "gas_ton": self.gas_ton,
            "exit_marketplace": venue,
            "exit_fee_percent": sell_fee_percent(venue),
            "floor_ton": floor_price,
            "net_value_ton": None if proceeds is None else proceeds.quantize(TON, rounding=ROUND_HALF_UP),
            "profit_ton": None if profit is None else profit.quantize(TON, rounding=ROUND_HALF_UP),
            "profit_percent": percent,
            "valued": valued,
        }

    async def list(self, user_id: int, include_closed: bool = True) -> dict:
        query = select(Position).where(Position.user_id == user_id)
        if not include_closed:
            query = query.where(Position.closed_at.is_(None))
        rows = list((await self.session.scalars(query.order_by(Position.opened_at.desc()))).all())
        gift_ids = [row.gift_id for row in rows]
        floors = await self._floors(gift_ids)
        gifts = await self._gifts(gift_ids)
        items = [self._card(row, gifts.get(row.gift_id), floors.get(row.gift_id)) for row in rows]

        invested = sum(
            (item["cost_ton"] for item in items if item["is_open"]), Decimal(0)
        )
        market_value = sum(
            (item["net_value_ton"] for item in items if item["is_open"] and item["valued"]),
            Decimal(0),
        )
        unrealized = sum(
            (item["profit_ton"] for item in items if item["is_open"] and item["valued"]),
            Decimal(0),
        )
        realized = sum(
            (item["profit_ton"] for item in items if not item["is_open"] and item["valued"]),
            Decimal(0),
        )
        closed = [item for item in items if not item["is_open"] and item["valued"]]
        winners = [item for item in closed if item["profit_ton"] > 0]
        # Percent is against invested capital, and only over lots we can price.
        priced = sum(
            (item["cost_ton"] for item in items if item["is_open"] and item["valued"]),
            Decimal(0),
        )
        summary = {
            "open_count": sum(1 for item in items if item["is_open"]),
            "closed_count": len(closed),
            "unvalued_count": sum(1 for item in items if item["is_open"] and not item["valued"]),
            "invested_ton": invested.quantize(TON, rounding=ROUND_HALF_UP),
            "market_value_ton": market_value.quantize(TON, rounding=ROUND_HALF_UP),
            "unrealized_ton": unrealized.quantize(TON, rounding=ROUND_HALF_UP),
            "unrealized_percent": (
                (unrealized / priced * Decimal(100)).quantize(CENT, rounding=ROUND_HALF_UP)
                if priced > 0
                else None
            ),
            "realized_ton": realized.quantize(TON, rounding=ROUND_HALF_UP),
            "win_rate_percent": (
                (Decimal(len(winners)) / Decimal(len(closed)) * Decimal(100)).quantize(CENT)
                if closed
                else None
            ),
        }
        return {"items": items, "summary": summary}

    async def card(self, position: Position) -> dict:
        floors = await self._floors([position.gift_id])
        gifts = await self._gifts([position.gift_id])
        return self._card(position, gifts.get(position.gift_id), floors.get(position.gift_id))
