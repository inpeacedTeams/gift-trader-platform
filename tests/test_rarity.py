from decimal import Decimal

import pytest

from app.market.getgems import GetGemsParser
from app.market.rarity import rarest, rarity_tier, split_rarity, strip_rarity
from app.market.tonnel import TonnelParser


class FakePostHttp:
    def __init__(self, pages):
        self.pages = list(pages)

    async def post_json(self, marketplace, url, *, headers=None, params=None, json_body=None):
        return self.pages.pop(0) if self.pages else []


def test_split_rarity_returns_name_and_percentage():
    assert split_rarity("Albino (1.5%)") == ("Albino", Decimal("1.5"))
    assert split_rarity("Albino") == ("Albino", None)
    assert split_rarity(None) == (None, None)
    assert split_rarity("   ") == (None, None)


def test_split_rarity_rejects_impossible_percentages():
    """A share above 100 is a format change, not a rarity."""
    assert split_rarity("Albino (140%)") == ("Albino", None)
    assert split_rarity("Albino (0%)") == ("Albino", None)


def test_strip_rarity_still_returns_the_bare_name():
    assert strip_rarity("Cyberpunk (0.2%)") == "Cyberpunk"


def test_rarest_ignores_unknown_traits():
    assert rarest(Decimal("5"), None, Decimal("0.4")) == Decimal("0.4")
    assert rarest(None, None) is None


def test_rarity_tier_buckets_by_the_scarcest_trait():
    assert rarity_tier(Decimal("8"), Decimal("0.2")) == "legendary"
    assert rarity_tier(Decimal("0.9")) == "rare"
    assert rarity_tier(Decimal("4")) == "uncommon"
    assert rarity_tier(Decimal("20")) == "common"


def test_unknown_rarity_is_not_treated_as_common():
    assert rarity_tier(None, None, None) is None


@pytest.mark.asyncio
async def test_tonnel_keeps_backdrop_and_symbol():
    row = {
        "gift_id": "1",
        "gift_num": 42,
        "gift_name": "Plush Pepe",
        "model": "Albino (1.5%)",
        "backdrop": "Cyberpunk (0.2%)",
        "symbol": "Bow (3%)",
        "price": "90",
        "asset": "TON",
    }

    snapshot = await TonnelParser(FakePostHttp([[row]])).snapshot()

    listing = snapshot.listings[0]
    assert listing.model == "Albino"
    assert listing.backdrop == "Cyberpunk"
    assert listing.symbol == "Bow"
    assert listing.backdrop_rarity == Decimal("0.2")


def test_getgems_reads_traits_from_the_attribute_list():
    metadata = {
        "name": "Plush Pepe #42",
        "attributes": [
            {"trait_type": "Model", "value": "Albino"},
            {"trait_type": "Backdrop", "value": "Cyberpunk"},
            {"trait_type": "Symbol", "value": "Bow"},
        ],
    }

    traits = GetGemsParser._traits(metadata)

    assert traits["model"][0] == "Albino"
    assert traits["backdrop"][0] == "Cyberpunk"
    assert traits["symbol"][0] == "Bow"
