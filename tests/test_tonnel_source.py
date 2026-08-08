from decimal import Decimal

import pytest

from app.market.tonnel import PAGE_LIMIT, TonnelParser, gift_slug, strip_rarity


class FakePostHttp:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    async def post_json(self, marketplace, url, *, headers=None, params=None, json_body=None):
        self.calls.append(json_body or {})
        return self.pages.pop(0) if self.pages else []


def gift(gift_id, price="12.5", name="Plush Pepe", number=1234):
    return {
        "gift_id": gift_id,
        "gift_num": number,
        "gift_name": name,
        "model": "Albino (1.5%)",
        "price": price,
        "asset": "TON",
    }


def test_strip_rarity_keeps_bare_attribute_name():
    assert strip_rarity("Albino (1.5%)") == "Albino"
    assert strip_rarity("Albino") == "Albino"
    assert strip_rarity(None) is None


def test_gift_slug_drops_separators():
    assert gift_slug("Plush Pepe") == "PlushPepe"
    assert gift_slug("Durov's Cap") == "DurovsCap"
    assert gift_slug(None) is None


@pytest.mark.asyncio
async def test_tonnel_parses_listings_without_credentials():
    http = FakePostHttp([[gift("1")]])
    parser = TonnelParser(http)

    snapshot = await parser.snapshot()

    listing = snapshot.listings[0]
    assert listing.price_ton == Decimal("12.5")
    assert listing.model == "Albino"
    assert str(listing.url) == "https://t.me/nft/PlushPepe-1234"
    assert http.calls[0]["user_auth"] == ""


@pytest.mark.asyncio
async def test_tonnel_derives_telegram_cdn_image():
    http = FakePostHttp([[gift("1")]])

    snapshot = await TonnelParser(http).snapshot()

    assert str(snapshot.listings[0].image_url) == (
        "https://nft.fragment.com/gift/plushpepe-1234.medium.jpg"
    )


@pytest.mark.asyncio
async def test_tonnel_prefers_image_from_payload():
    row = gift("1")
    row["photo_url"] = "https://cdn.example.com/pepe.png"
    http = FakePostHttp([[row]])

    snapshot = await TonnelParser(http).snapshot()

    assert str(snapshot.listings[0].image_url) == "https://cdn.example.com/pepe.png"


@pytest.mark.asyncio
async def test_tonnel_stops_paginating_on_short_page():
    full_page = [gift(str(index)) for index in range(PAGE_LIMIT)]
    http = FakePostHttp([full_page, [gift("last")]])
    parser = TonnelParser(http)

    snapshot = await parser.snapshot()

    assert len(snapshot.listings) == PAGE_LIMIT + 1
    assert [call["page"] for call in http.calls] == [1, 2]


@pytest.mark.asyncio
async def test_tonnel_skips_rows_without_usable_price():
    http = FakePostHttp([[gift("1", price="0"), {"gift_id": "2"}, gift("3")]])
    parser = TonnelParser(http)

    snapshot = await parser.snapshot()

    assert [listing.listing_id for listing in snapshot.listings] == ["3"]
