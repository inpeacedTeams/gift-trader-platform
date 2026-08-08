"""Tells a seller when their lot stops being the cheapest one.

Every other alert in the product watches the market on behalf of a buyer.
This one watches it on behalf of a seller, and it is the difference between
noticing a stale listing in a week and noticing it in five minutes.

A warning goes out once per listing. A second one only follows if the
rival went lower again by a margin worth reacting to: repeating the same
news every crawl is how people learn to mute a bot.
"""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AlertEvent, SellerIdentity, UndercutNotice
from app.db.repositories.selling import SellingRepository

logger = logging.getLogger(__name__)

# Being a rounding error below is not being undercut.
MIN_GAP_PERCENT = Decimal("0.5")
# A repeat warning needs the rival to have moved this much lower again.
REPEAT_DROP_PERCENT = Decimal("2")


def _ton(value: Decimal) -> str:
    """90.000000000 is noise. Print what a person would write."""
    return format(Decimal(value).normalize(), "f")


def _message(item: dict) -> str:
    title = item["name"] or item["collection_name"] or f"Gift #{item['gift_id']}"
    traits = " · ".join(
        part for part in (item.get("model"), item.get("backdrop"), item.get("symbol")) if part
    )
    if traits:
        title = f"{title} · {traits}"
    lines = [
        "⚔️ Ваш лот перебили",
        "",
        title,
        f"Ваша цена: {_ton(item['price_ton'])} TON на {item['marketplace']}",
        f"Дешевле: {_ton(item['rival_price_ton'])} TON на {item['rival_marketplace']}",
        f"Разница: {item['undercut_percent']:.1f}%",
    ]
    if item.get("competitors"):
        lines.append(f"Похожих лотов в продаже: {item['competitors']}")
    if item.get("rival_url"):
        lines.extend(["", f"Лот конкурента: {item['rival_url']}"])
    if item.get("url"):
        lines.append(f"Ваш лот: {item['url']}")
    return "\n".join(lines)


class UndercutEvaluator:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.selling = SellingRepository(session)

    async def evaluate(self) -> int:
        """Check every seller who has a known identity. Returns alerts created."""
        user_ids = list(
            (await self.session.scalars(select(SellerIdentity.user_id).distinct())).all()
        )
        if not user_ids:
            return 0
        created = 0
        for user_id in user_ids:
            created += await self._for_user(user_id)
        return created

    async def _for_user(self, user_id: int) -> int:
        result = await self.selling.my_listings(user_id)
        undercut = [item for item in result["items"] if item["undercut"]]
        if not undercut:
            return 0

        listing_ids = [item["listing_id"] for item in undercut]
        notices = {
            notice.listing_id: notice
            for notice in (
                await self.session.scalars(
                    select(UndercutNotice).where(UndercutNotice.listing_id.in_(listing_ids))
                )
            ).all()
        }

        created = 0
        for item in undercut:
            gap = item["undercut_percent"] or Decimal(0)
            if gap < MIN_GAP_PERCENT:
                continue
            rival = item["rival_price_ton"]
            notice = notices.get(item["listing_id"])
            if notice is not None and not self._worth_repeating(notice.rival_price_ton, rival):
                continue
            self.session.add(
                AlertEvent(
                    rule_id=None,
                    user_id=user_id,
                    gift_id=item["gift_id"],
                    message=_message(item),
                    observed_value=rival,
                )
            )
            if notice is None:
                self.session.add(
                    UndercutNotice(
                        user_id=user_id,
                        listing_id=item["listing_id"],
                        my_price_ton=item["price_ton"],
                        rival_price_ton=rival,
                    )
                )
            else:
                notice.my_price_ton = item["price_ton"]
                notice.rival_price_ton = rival
            created += 1
        return created

    @staticmethod
    def _worth_repeating(previous: Decimal, current: Decimal) -> bool:
        """Only if the competition actually went lower again.

        A rival raising their price, or holding it, is not news. The user
        already knows they are being undercut; saying it twice teaches them
        to ignore the third time.
        """
        if previous <= 0:
            return current < previous
        drop = (previous - current) / previous * Decimal(100)
        return drop >= REPEAT_DROP_PERCENT
