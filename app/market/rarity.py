"""Attribute rarity: the part of a gift's value that is not the model.

Marketplaces publish rarity as a suffix on the attribute name, for example
"Albino (1.5%)". The number is the share of the collection carrying that
trait, so smaller means rarer. We keep both halves: the bare name so the same
gift matches across marketplaces, and the percentage so pricing can tell a
legendary backdrop apart from a plain one.

Nothing here guesses. A trait with no published percentage stays unrated
rather than being assumed common.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Any

# "Albino (1.5%)" -> name "Albino", percent 1.5
RARITY_SUFFIX = re.compile(r"\s*\(\s*([0-9]*\.?[0-9]+)\s*%\s*\)\s*$")

# Upper bound of each tier, rarest first. Anything above the last bound is
# common: a trait worn by one gift in twenty carries no premium.
TIERS: tuple[tuple[Decimal, str], ...] = (
    (Decimal("0.3"), "legendary"),
    (Decimal("1"), "rare"),
    (Decimal("5"), "uncommon"),
)
COMMON = "common"
TIER_NAMES: tuple[str, ...] = tuple(label for _, label in TIERS) + (COMMON,)


def split_rarity(value: Any) -> tuple[str | None, Decimal | None]:
    """Separate an attribute into its name and its published rarity.

    A percentage outside (0, 100] is a format change, not a rarity, so the
    name survives and the number is dropped instead of poisoning valuations.
    """
    if value is None:
        return None, None
    text = str(value).strip()
    if not text:
        return None, None
    match = RARITY_SUFFIX.search(text)
    if match is None:
        return text, None
    name = text[: match.start()].strip() or None
    try:
        percent = Decimal(match.group(1))
    except InvalidOperation:
        return name, None
    if percent <= 0 or percent > 100:
        return name, None
    return name, percent


def strip_rarity(value: Any) -> str | None:
    """Just the attribute name, for call sites that do not price rarity."""
    return split_rarity(value)[0]


def rarest(*percents: Decimal | None) -> Decimal | None:
    """The scarcest known trait. Unknown traits are ignored, not counted."""
    known = [percent for percent in percents if percent is not None]
    return min(known) if known else None


def rarity_tier(*percents: Decimal | None) -> str | None:
    """Bucket a gift by its scarcest trait.

    Returns None when nothing is known. Absence of data is not commonness,
    and a gift with no rarity information must not be compared as if it had.
    """
    percent = rarest(*percents)
    if percent is None:
        return None
    for bound, label in TIERS:
        if percent <= bound:
            return label
    return COMMON
