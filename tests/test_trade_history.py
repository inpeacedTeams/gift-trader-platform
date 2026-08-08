from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.market.history import TonnelSaleHistory, parse_timestamp, trade_identity
from app.market.models import SourceUnavailable


class FakePostHttp:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    async def post_json(self, marketplace, url, *, headers=None, params=None, json_body=None):
        self.calls.append(json_body or {})
        return self.pages.pop(0) if self.pages else []


def sale(external_id="sale-1", price="120", asset="TON"):
    return {
        "_id": external_id,
        "gift_name": "Plush Pepe",
        "gift_num": 834,
        "model": "Albino (1.5%)",
        "price": price,
        "asset": asset,
        "timestamp": 1786000000,
        "seller": 111,
        "buyer": 222,
    }


def test_parse_timestamp_handles_seconds_millis_and_iso():
    assert parse_timestamp(1786000000).year == 2026
    assert parse_timestamp(1786000000000).year == 2026
    assert parse_timestamp("2026-08-08T03:00:00Z").tzinfo is timezone.utc
    assert parse_timestamp("not a date") is None


@pytest.mark.asyncio
async def test_fetch_without_auth_reports_unavailable():
    with pytest.raises(SourceUnavailable) as error:
        await TonnelSaleHistory(FakePostHttp([])).fetch()

    assert "TONNEL_AUTH_DATA" in error.value.reason


@pytest.mark.asyncio
async def test_fetch_parses_completed_sales():
    http = FakePostHttp([[sale()]])

    trades = await TonnelSaleHistory(http, auth_data="query_id=abc").fetch()

    assert trades[0].price_ton == Decimal("120")
    assert trades[0].model == "Albino"
    assert trades[0].buyer == "222"
    assert http.calls[0]["type"] == "SALE"


@pytest.mark.asyncio
async def test_non_ton_sales_are_ignored():
    http = FakePostHttp([[sale(asset="USDT"), sale(external_id="sale-2")]])

    trades = await TonnelSaleHistory(http, auth_data="query_id=abc").fetch()

    assert [trade.external_id for trade in trades] == ["sale-2"]


@pytest.mark.asyncio
async def test_trade_identity_matches_the_listing_key_scheme():
    http = FakePostHttp([[{**sale(), "nft_address": "EQGift"}]])

    trades = await TonnelSaleHistory(http, auth_data="query_id=abc").fetch()

    assert trade_identity(trades[0]) == "canonical:eqgift"


def test_trade_without_identity_is_unresolved():
    from app.market.history import Trade

    trade = Trade(
        marketplace="tonnel",
        external_id="x",
        price_ton=Decimal("5"),
        traded_at=datetime.now(timezone.utc),
        source_url="https://gifts2.tonnel.network/api/saleHistory",
    )

    assert trade_identity(trade).startswith("unresolved:")
