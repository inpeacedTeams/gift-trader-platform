from decimal import Decimal

import pytest

from app.market.models import SourceUnavailable
from app.market.mrkt import PAGE_SIZE, MrktParser


class FakeHttp:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    async def post_json(self, marketplace, url, *, headers=None, params=None, json_body=None):
        self.calls.append({"url": url, "headers": headers or {}, "body": json_body or {}})
        return self.pages.pop(0) if self.pages else {}


def gift(gift_id, price="12500000000", number=834):
    return {
        "id": gift_id,
        "collectionName": "Plush Pepe",
        "model": "Albino (1.5%)",
        "number": number,
        "price": price,
    }


def page(gifts, cursor=""):
    return {"gifts": gifts, "cursor": cursor}


@pytest.mark.asyncio
async def test_without_credentials_the_source_is_unavailable():
    with pytest.raises(SourceUnavailable) as error:
        await MrktParser(FakeHttp([])).snapshot()

    assert "MRKT_TOKEN" in error.value.reason


@pytest.mark.asyncio
async def test_nanoton_prices_are_converted():
    http = FakeHttp([page([gift("1")])])

    snapshot = await MrktParser(http, token="t").snapshot()

    assert snapshot.listings[0].price_ton == Decimal("12.5")
    assert snapshot.listings[0].model == "Albino"


@pytest.mark.asyncio
async def test_plain_ton_prices_survive_untouched():
    http = FakeHttp([page([gift("1", price="44")])])

    snapshot = await MrktParser(http, token="t").snapshot()

    assert snapshot.listings[0].price_ton == Decimal("44")


@pytest.mark.asyncio
async def test_the_cursor_walks_the_whole_book():
    first = page([gift(str(index)) for index in range(PAGE_SIZE)], cursor="next")
    second = page([gift("last")])
    http = FakeHttp([first, second])

    snapshot = await MrktParser(http, token="t").snapshot()

    assert len(snapshot.listings) == PAGE_SIZE + 1
    assert http.calls[1]["body"]["cursor"] == "next"


@pytest.mark.asyncio
async def test_init_data_is_exchanged_for_a_token():
    http = FakeHttp([{"token": "minted"}, page([gift("1")])])

    snapshot = await MrktParser(http, init_data="query_id=abc").snapshot()

    assert http.calls[0]["url"].endswith("/auth")
    assert http.calls[1]["headers"]["Authorization"] == "minted"
    assert len(snapshot.listings) == 1


@pytest.mark.asyncio
async def test_stale_init_data_reports_a_clear_reason():
    http = FakeHttp([{}])

    with pytest.raises(SourceUnavailable) as error:
        await MrktParser(http, init_data="query_id=abc").snapshot()

    assert "stale" in error.value.reason
