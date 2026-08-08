from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, Listing, Position
from app.db.repositories.arbitrage import DEFAULT_FEES, DEFAULT_GAS_TON

# Same fallback the arbitrage scanner uses for venues it has no entry for.
DEFAULT_SELL_FEE = Decimal("5")
TON = Decimal("0.001")
PCT = Decimal("0.01")


class PositionRepository:
    """The user's own book, priced against the live market.

    Profit is computed on read rather than stored: the moment a floor moves,
    a stored P&L is a lie, and this product's whole claim is that its numbers
    are current.
    """

    def __init__(
        self,
        session: AsyncSession,
        fees: dict[str, Decimal] | None = None,
        gas_ton: Decimal = DEFAULT_GAS_TON,
    ):
        self.session = session
        self.fees = fees or DEFAULT_FEES
        self.gas_ton = gas_ton

    def _fee(self, marketplace: str | None) -> Decimal:
        return self.fees.get(marketplace or "", DEFAULT_SELL_FEE)

    def _net_sale(self, marketplace: str | None, price: Decimal) -> Decimal:
        return price - price * self._fee(marketplace) / Decimal(100)

    async def _cheapest_venues(self, gift_ids: list[int]) -> dict[int, str]:
        """Venue holding the floor listing, because its fee sets the exit."""
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

    async def cards(self, user_id: int, include_closed: bool = True) -> list[dict]:
        stmt = (
            select(
                Position.id,
                Position.gift_id,
                Position.marketplace,
                Position.buy_price_ton,
                Position.quantity,
                Position.opened_at,
                Position.sell_price_ton,
                Position.sell_marketplace,
                Position.closed_at,
                Position.note,
                Gift.name,
                Gift.model,
                Gift.image_url,
                Gift.rarity_tier,
                Gift.gift_number,
                Collection.name.label("collection_name"),
                func.min(Listing.price_ton).label("floor_ton"),
                func.percentile_cont(0.5).within_group(Listing.price_ton.asc()).label("median_ton"),
            )
            .join(Gift, Gift.id == Position.gift_id)
            .outerjoin(Listing, (Listing.gift_id == Gift.id) & Listing.active.is_(True))
            .outerjoin(Collection, Collection.id == Gift.collection_id)
            .where(Position.user_id == user_id)
            .group_by(Position.id, Gift.id, Collection.name)
            # Open positions first: they are the ones that still need a decision.
            .order_by(Position.closed_at.is_(None).desc(), Position.opened_at.desc())
        )
        if not include_closed:
            stmt = stmt.where(Position.closed_at.is_(None))
        rows = (await self.session.execute(stmt)).all()
        venues = await self._cheapest_venues([row.gift_id for row in rows])

        cards: list[dict] = []
        for row in rows:
            quantity = max(int(row.quantity or 1), 1)
            buy = Decimal(row.buy_price_ton)
            # Gas was spent getting in, so it belongs to the cost basis.
            cost_per_unit = buy + self.gas_ton
            is_open = row.closed_at is None or row.sell_price_ton is None
            floor = Decimal(row.floor_ton) if row.floor_ton is not None else None

            if is_open:
                venue = venues.get(row.gift_id) or row.marketplace
                exit_net = self._net_sale(venue, floor) if floor is not None else None
            else:
                venue = row.sell_marketplace or row.marketplace
                exit_net = self._net_sale(venue, Decimal(row.sell_price_ton))

            profit = (exit_net - cost_per_unit) * quantity if exit_net is not None else None
            basis = cost_per_unit * quantity
            roi = profit / basis * Decimal(100) if profit is not None and basis > 0 else None

            cards.append(
                {
                    "id": row.id,
                    "gift_id": row.gift_id,
                    "name": row.name or row.collection_name,
                    "model": row.model,
                    "image_url": row.image_url,
                    "rarity_tier": row.rarity_tier,
                    "gift_number": row.gift_number,
                    "collection_name": row.collection_name,
                    "marketplace": row.marketplace,
                    "buy_price_ton": buy,
                    "quantity": quantity,
                    "opened_at": row.opened_at,
                    "closed_at": row.closed_at,
                    "sell_price_ton": row.sell_price_ton,
                    "sell_marketplace": row.sell_marketplace,
                    "note": row.note,
                    "floor_ton": floor,
                    "median_ton": Decimal(row.median_ton) if row.median_ton is not None else None,
                    "exit_venue": venue,
                    "exit_net_ton": exit_net.quantize(TON) if exit_net is not None else None,
                    "cost_basis_ton": basis.quantize(TON),
                    "profit_ton": profit.quantize(TON) if profit is not None else None,
                    "roi_percent": roi.quantize(PCT) if roi is not None else None,
                    "is_open": is_open,
                }
            )
        return cards

    def summary(self, cards: list[dict]) -> dict:
        """Book level numbers, derived from the same cards the UI renders.

        Positions whose gift has no active listing are counted separately
        instead of being valued at zero, which would report a fake loss.
        """
        open_cards = [card for card in cards if card["is_open"]]
        closed_cards = [card for card in cards if not card["is_open"]]
        priced = [card for card in open_cards if card["exit_net_ton"] is not None]

        invested = sum((card["cost_basis_ton"] for card in open_cards), Decimal(0))
        market_value = sum(
            (card["exit_net_ton"] * card["quantity"] for card in priced), Decimal(0)
        )
        unrealized = sum((card["profit_ton"] for card in priced), Decimal(0))
        realized = sum(
            (card["profit_ton"] for card in closed_cards if card["profit_ton"] is not None),
            Decimal(0),
        )
        wins = [card for card in closed_cards if (card["profit_ton"] or Decimal(0)) > 0]
        win_rate = (
            Decimal(len(wins)) / Decimal(len(closed_cards)) * Decimal(100) if closed_cards else None
        )
        return {
            "open_count": len(open_cards),
            "closed_count": len(closed_cards),
            "unpriced_count": len(open_cards) - len(priced),
            "invested_ton": invested.quantize(TON),
            "market_value_ton": market_value.quantize(TON),
            "unrealized_ton": unrealized.quantize(TON),
            "realized_ton": realized.quantize(TON),
            "wins": len(wins),
            "win_rate_percent": win_rate.quantize(PCT) if win_rate is not None else None,
        }
