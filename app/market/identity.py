import re
import unicodedata
from hashlib import sha256

from .models import Listing


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[^a-z0-9а-яё]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_address(value: str | None) -> str:
    return (value or "").strip().casefold()


def slugify(value: str | None) -> str:
    """'Snoop Dogg' -> 'snoop-dogg'. Empty when there is nothing usable."""
    return normalize_text(value).replace(" ", "-")


def canonical_collection_key(listing: Listing) -> str | None:
    """Stable identity for the collection a listing belongs to.

    On-chain address wins when a source provides one. Marketplaces that only
    expose a gift name fall back to a slug so the same collection still groups
    across sources.
    """
    address = normalize_address(listing.collection_id)
    if address:
        return address
    slug = slugify(listing.collection_name or listing.name)
    return f"name:{slug}" if slug else None


def canonical_gift_key(listing: Listing) -> str:
    """Build a stable key only from identity fields, never from price or URL.

    A collection address plus Telegram gift number is authoritative. For
    marketplace records without an address, normalized collection/name/model
    identity is used and marked as a derived key.
    """
    if listing.canonical_id:
        return f"canonical:{normalize_address(listing.canonical_id)}"
    if listing.collection_id and listing.gift_number is not None:
        return f"chain:{normalize_address(listing.collection_id)}:{listing.gift_number}"
    collection = normalize_text(listing.collection_name or listing.collection_id)
    name = normalize_text(listing.name)
    if collection and name and listing.model:
        name = f"{name} {normalize_text(listing.model)}"
    if collection and name:
        raw = f"derived:{collection}:{name}"
        return "derived:" + sha256(raw.encode()).hexdigest()[:24]
    return f"unresolved:{listing.marketplace}:{normalize_address(listing.gift_id)}"
