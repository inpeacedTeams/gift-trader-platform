from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Gift, Listing, SellerIdentity
from app.market.economics import net_proceeds

TON = Decimal("0.001")
CENT = Decimal("0.01")
# Peer group: the same collection, model and rarity tier. A plain backdrop is
# not competition for a one in five hundred one.
PeerKey = tuple[int | None, str | None, str | None]


def peer_key(gift: Gift) -> PeerKey:
    return (gift.collection_id, gift.model, gift.rarity_tier)


class SellingRepository:
    """The user's own listings, seen from the other side of the book.

    A seller does not care what the floor is, they care whether somebody is
    standing in front of them. Every row here answers that: the cheapest
    comparable lot that is not theirs, and how far below it sits.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def identities(self, user_id: int) -> list[SellerIdentity]:
        return list(
            (
                await self.session.scalars(
                    select(SellerIdentity)
                    .where(SellerIdentity.user_id == user_id)
                    .order_by(SellerIdentity.created_at.asc())
                )
            ).all()
        )

    @staticmethod
    def owns(identities: list[SellerIdentity], seller: str | None, marketplace: str) -> bool:
        """Does this listing belong to the user.

        A market wide identity matches anywhere; a scoped one only on its own
        venue, so the same numeric handle on a different marketplace is not
        mistaken for the same person.
        """
        if not seller:
            return False
        for identity in identities:
            if identity.seller != seller:
                continue
            if identity.marketplace is None or identity.marketplace == marketplace:
                return True
        return False

    async def my_listings(self, user_id: int) -> dict:
        identities = await self.identities(user_id)
        if not identities:
            return {"items": [], "summary": self._summary([])}

        handles = {identity.seller for identity in identities}
        mine = (
            await self.session.execute(
                select(Listing, Gift)
                .join(Gift, Gift.id == Listing.gift_id)
                .where(Listing.active.is_(True), Listing.seller.in_(handles))
                .order_by(Listing.price_ton.asc())
            )
        ).all()
        mine = [
            (listing, gift)
            for listing, gift in mine
            if self.owns(identities, listing.seller, listing.marketplace)
        ]
        if not mine:
            return {"items": [], "summary": self._summary([])}

        rivals = await self._rivals({peer_key(gift) for _, gift in mine}, identities)
        names = await self._collection_names({gift.collection_id for _, gift in mine})

        items = []
        for listing, gift in mine:
            rival = rivals.get(peer_key(gift))
            price = listing.price_ton
            undercut = rival is not None and rival["price_ton"] < price
            gap = (
                ((price - rival["price_ton"]) / price * Decimal(100)).quantize(
                    CENT, rounding=ROUND_HALF_UP
                )
                if undercut
                else None
            )
            items.append(
                {
                    "listing_id": listing.id,
                    "gift_id": gift.id,
                    "name": gift.name,
                    "model": gift.model,
                    "backdrop": gift.backdrop,
                    "symbol": gift.symbol,
                    "rarity_tier": gift.rarity_tier,
                    "gift_number": gift.gift_number,
                    "image_url": gift.image_url,
                    "collection_name": names.get(gift.collection_id),
                    "marketplace": listing.marketplace,
                    "price_ton": price,
                    "net_proceeds_ton": net_proceeds(listing.marketplace, price).quantize(
                        TON, rounding=ROUND_HALF_UP
                    ),
                    "url": listing.url,
                    "listed_at": listing.first_seen_at,
                    "rival_price_ton": rival["price_ton"] if rival else None,
                    "rival_marketplace": rival["marketplace"] if rival else None,
                    "rival_url": rival["url"] if rival else None,
                    "rival_gift_id": rival["gift_id"] if rival else None,
                    "competitors": rival["count"] if rival else 0,
                    "undercut": undercut,
                    "undercut_percent": gap,
                }
            )
        items.sort(key=lambda item: (not item["undercut"], -(item["undercut_percent"] or 0)))
        return {"items": items, "summary": self._summary(items)}

    @staticmethod
    def _summary(items: list[dict]) -> dict:
        listed = sum((item["price_ton"] for item in items), Decimal(0))
        net = sum((item["net_proceeds_ton"] for item in items), Decimal(0))
        return {
            "listed_count": len(items),
            "undercut_count": sum(1 for item in items if item["undercut"]),
            "listed_value_ton": listed.quantize(TON, rounding=ROUND_HALF_UP),
            "net_value_ton": net.quantize(TON, rounding=ROUND_HALF_UP),
        }

    async def _collection_names(self, collection_ids: set[int | None]) -> dict[int, str | None]:
        known = {item for item in collection_ids if item is not None}
        if not known:
            return {}
        rows = (
            await self.session.execute(
                select(Collection.id, Collection.name).where(Collection.id.in_(known))
            )
        ).all()
        return {row.id: row.name for row in rows}

    async def _rivals(
        self, keys: set[PeerKey], identities: list[SellerIdentity]
    ) -> dict[PeerKey, dict]:
        """Cheapest comparable lot that is not the user's own, per peer group.

        Scoped to the collections the user actually sells in, because scanning
        the whole book to answer a question about a handful of lots is waste.
        """
        collections = {key[0] for key in keys if key[0] is not None}
        if not collections:
            return {}
        rows = (
            await self.session.execute(
                select(
                    Gift.id,
                    Gift.collection_id,
                    Gift.model,
                    Gift.rarity_tier,
                    Listing.marketplace,
                    Listing.price_ton,
                    Listing.url,
                    Listing.seller,
                )
                .join(Listing, (Listing.gift_id == Gift.id) & Listing.active.is_(True))
                .where(Gift.collection_id.in_(collections))
                .order_by(Listing.price_ton.asc())
            )
        ).all()

        rivals: dict[PeerKey, dict] = {}
        for row in rows:
            key = (row.collection_id, row.model, row.rarity_tier)
            if key not in keys:
                continue
            if self.owns(identities, row.seller, row.marketplace):
                continue
            entry = rivals.get(key)
            if entry is None:
                # Price ordered, so the first foreign lot in a group is its floor.
                rivals[key] = {
                    "gift_id": row.id,
                    "marketplace": row.marketplace,
                    "price_ton": row.price_ton,
                    "url": row.url,
                    "count": 1,
                }
            else:
                entry["count"] += 1
        return rivals
