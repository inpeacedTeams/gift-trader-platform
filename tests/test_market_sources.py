from decimal import Decimal

import pytest

from app.market.getgems import GetGemsParser
from app.market.models import SourceUnavailable
from app.market.portals import PortalsParser


class FakeHttp:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    async def get_json(self, marketplace, url, *, headers=None, params=None):
        self.calls.append({"url": url, "headers": headers or {}, "params": params or {}})
        return self.payloads.pop(0) if self.payloads else {}


def getgems_item(address, market_name="Getgems", nanoton="12500000000"):
    return {
        "address": address,
        "metadata": {"name": "Toy Bear"},
        "collection": {"address": "EQcollection", "name": "Toy Bears"},
        "sale": {
            "address": f"{address}-sale",
            "market": {"name": market_name},
            "price": {"token_name": "TON", "value": nanoton},
        },
    }


@pytest.mark.asyncio
async def test_getgems_reads_tonapi_sale_market_and_price():
    http = FakeHttp([{"nft_items": [getgems_item("EQgift1")]}])
    parser = GetGemsParser(http, ["EQcollection"], api_token="secret-token")

    snapshot = await parser.snapshot()

    assert [listing.price_ton for listing in snapshot.listings] == [Decimal("12.5")]
    assert snapshot.listings[0].canonical_id == "EQgift1"
    assert http.calls[0]["headers"]["Authorization"] == "Bearer secret-token"


@pytest.mark.asyncio
async def test_getgems_skips_listings_from_other_marketplaces():
    http = FakeHttp([{"nft_items": [getgems_item("EQgift1", market_name="Fragment")]}])
    parser = GetGemsParser(http, ["EQcollection"])

    snapshot = await parser.snapshot()

    assert snapshot.listings == []


@pytest.mark.asyncio
async def test_getgems_without_collections_reports_unavailable():
    parser = GetGemsParser(FakeHttp([]), [])

    with pytest.raises(SourceUnavailable) as error:
        await parser.snapshot()

    assert "GETGEMS_COLLECTION_ADDRESSES" in error.value.reason


@pytest.mark.asyncio
async def test_portals_without_auth_reports_unavailable():
    parser = PortalsParser(FakeHttp([]))

    with pytest.raises(SourceUnavailable) as error:
        await parser.snapshot()

    assert "PORTALS_AUTH_DATA" in error.value.reason


@pytest.mark.asyncio
async def test_portals_parses_search_results_with_auth_header():
    http = FakeHttp(
        [
            {
                "results": [
                    {
                        "id": "65c83c42",
                        "tg_id": "294992",
                        "collection_id": "060d4cef",
                        "owner_id": 488711606,
                        "name": "Toy Bear",
                        "price": "44",
                        "attributes": [{"type": "model", "value": "Wizard"}],
                    }
                ]
            }
        ]
    )
    parser = PortalsParser(http, auth_data="query_id=abc")

    snapshot = await parser.snapshot()

    assert snapshot.listings[0].price_ton == Decimal("44")
    assert snapshot.listings[0].model == "Wizard"
    assert http.calls[0]["headers"]["Authorization"] == "tma query_id=abc"
