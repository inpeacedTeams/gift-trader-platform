"""Evaluates gift price rules against a fresh crawl.

Rules are checked here rather than inside the persist loop so a rule sees
the final floor across every marketplace, not whichever listing happened to
be written last.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AlertEvent, AlertRule, Collection, Gift, Listing, PriceSnapshot

GIFT_RULES = ("price_below", "price_above", "listed_below", "change_percent")
# A crawl runs every few minutes; without this one falling price would
# notify on every single pass.
COOLDOWN = timedelta(minutes=30)


def _format_ton(value: Decimal | None) -> str:
    if value is None:
        return "n/a"
    number = Decimal(value).normalize()
    text = f"{number:f}"
    return f"{text} TON"


class GiftAlertEvaluator:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def evaluate(self, gift_ids: set[int]) -> int:
        """Check every active gift rule touching the gifts we just crawled."""
        if not gift_ids:
            return 0
        rules = list(
            (
                await self.session.scalars(
                    select(AlertRule).where(
                        AlertRule.is_active.is_(True),
                        AlertRule.rule_type.in_(GIFT_RULES),
                    )
                )
            ).all()
        )
        if not rules:
            return 0
        # A rule without a gift_id watches the whole market.
        watched = {rule.gift_id for rule in rules if rule.gift_id is not None}
        relevant = gift_ids if any(rule.gift_id is None for rule in rules) else gift_ids & watched
        if not relevant:
            return 0
        state = await self._state(relevant)
        created = 0
        for rule in rules:
            targets = [rule.gift_id] if rule.gift_id is not None else list(relevant)
            for gift_id in targets:
                snapshot = state.get(gift_id)
                if snapshot is None:
                    continue
                message = self._message(rule, snapshot)
                if message is None:
                    continue
                if await self._on_cooldown(rule.id, gift_id):
                    continue
                self.session.add(
                    AlertEvent(
                        rule_id=rule.id,
                        user_id=rule.user_id,
                        gift_id=gift_id,
                        message=message,
                        observed_value=snapshot["floor"],
                    )
                )
                created += 1
        return created

    async def _state(self, gift_ids: set[int]) -> dict[int, dict]:
        """Current floor, venue and identity for each gift, in one query."""
        rows = (
            await self.session.execute(
                select(
                    Gift.id,
                    Gift.name,
                    Gift.model,
                    Collection.name.label("collection_name"),
                    func.min(Listing.price_ton).label("floor"),
                )
                .join(Listing, (Listing.gift_id == Gift.id) & Listing.active.is_(True))
                .outerjoin(Collection, Collection.id == Gift.collection_id)
                .where(Gift.id.in_(gift_ids))
                .group_by(Gift.id, Collection.name)
            )
        ).all()
        state: dict[int, dict] = {}
        for row in rows:
            cheapest = await self.session.execute(
                select(Listing.marketplace, Listing.url, Listing.price_ton)
                .where(Listing.gift_id == row.id, Listing.active.is_(True))
                .order_by(Listing.price_ton.asc())
                .limit(1)
            )
            venue = cheapest.first()
            state[row.id] = {
                "name": row.name,
                "model": row.model,
                "collection": row.collection_name,
                "floor": row.floor,
                "marketplace": venue.marketplace if venue else None,
                "url": venue.url if venue else None,
                "previous": await self._previous_floor(row.id),
            }
        return state

    async def _previous_floor(self, gift_id: int) -> Decimal | None:
        """Floor from the pass before this one, for percentage rules."""
        rows = (
            await self.session.scalars(
                select(PriceSnapshot.floor_ton)
                .where(PriceSnapshot.gift_id == gift_id, PriceSnapshot.floor_ton.is_not(None))
                .order_by(PriceSnapshot.observed_at.desc())
                .limit(2)
            )
        ).all()
        return rows[1] if len(rows) > 1 else None

    def _message(self, rule: AlertRule, snapshot: dict) -> str | None:
        floor = snapshot["floor"]
        if floor is None:
            return None
        title = snapshot["name"] or snapshot["collection"] or "Gift"
        if snapshot["model"]:
            title = f"{title} · {snapshot['model']}"
        venue = snapshot["marketplace"] or "market"

        if rule.rule_type in ("price_below", "listed_below") and floor <= rule.threshold:
            head = "📉 Цена ниже порога"
            detail = f"Порог: ниже {_format_ton(rule.threshold)}"
        elif rule.rule_type == "price_above" and floor >= rule.threshold:
            head = "📈 Цена выше порога"
            detail = f"Порог: выше {_format_ton(rule.threshold)}"
        elif rule.rule_type == "change_percent":
            previous = snapshot["previous"]
            if not previous or previous <= 0:
                return None
            change = (floor - previous) / previous * Decimal(100)
            if abs(change) < rule.threshold:
                return None
            head = "📉 Резкое падение" if change < 0 else "📈 Резкий рост"
            detail = f"Изменение {change:+.1f}%, было {_format_ton(previous)}\nПорог: движение от {rule.threshold}%"
        else:
            return None

        lines = [f"{head}", "", title, f"{_format_ton(floor)} на {venue}"]
        if snapshot["previous"] and rule.rule_type != "change_percent":
            lines.append(f"было {_format_ton(snapshot['previous'])}")
        lines.extend(["", detail])
        if snapshot["url"]:
            lines.extend(["", snapshot["url"]])
        return "\n".join(lines)

    async def _on_cooldown(self, rule_id: int, gift_id: int) -> bool:
        since = datetime.now(timezone.utc) - COOLDOWN
        recent = await self.session.scalar(
            select(AlertEvent.id)
            .where(
                AlertEvent.rule_id == rule_id,
                AlertEvent.gift_id == gift_id,
                AlertEvent.created_at >= since,
            )
            .limit(1)
        )
        return recent is not None
