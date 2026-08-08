import re
import unicodedata
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Collection, Gift, PriceSnapshot

def normalize(value: str | None) -> str:
    if not value: return ""
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9а-яё]+", " ", value)).strip()

def metadata_value(metadata: dict, key: str) -> str | None:
    direct = metadata.get(key)
    if isinstance(direct, str): return direct
    for attribute in metadata.get("attributes", []) or []:
        if not isinstance(attribute, dict): continue
        trait = str(attribute.get("trait_type") or attribute.get("type") or "").casefold()
        if trait == key.casefold():
            value = attribute.get("value"); return str(value) if value is not None else None
    return None

async def resolve_gift(session: AsyncSession, *, nft_address: str, collection_address: str | None, metadata: dict) -> tuple[Gift | None, str, Decimal | None, int]:
    exact = await session.scalar(select(Gift).where(Gift.canonical_id == nft_address))
    if exact: return exact, "canonical_nft_address", Decimal("100"), 1
    if not collection_address: return None, "missing_collection", None, 0
    collection = await session.scalar(select(Collection).where(Collection.chain_address == collection_address))
    if collection is None: return None, "unknown_collection", None, 0
    name = normalize(metadata.get("name")); model = normalize(metadata_value(metadata, "model"))
    if not name or not model: return None, "missing_name_or_model", None, 0
    candidates = list((await session.scalars(select(Gift).where(Gift.collection_id == collection.id, Gift.name.is_not(None), Gift.model.is_not(None)))).all())
    matches = [gift for gift in candidates if normalize(gift.name) == name and normalize(gift.model) == model]
    if len(matches) != 1: return None, "ambiguous_identity" if matches else "no_exact_match", None, len(matches)
    return matches[0], "collection_name_model_exact", Decimal("85"), 1

async def latest_floor(session: AsyncSession, gift: Gift | None) -> Decimal | None:
    if gift is None: return None
    snapshot = await session.scalar(select(PriceSnapshot).where(PriceSnapshot.gift_id == gift.id).order_by(PriceSnapshot.observed_at.desc()).limit(1))
    return snapshot.floor_ton if snapshot else None
