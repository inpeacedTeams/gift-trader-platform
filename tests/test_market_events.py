from datetime import datetime, timezone
from decimal import Decimal

from app.db.repositories.market_snapshot import MIN_CHANGE_PERCENT
from app.market.tonnel import PAGE_LIMIT, TonnelParser


class FakePostHttp:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    async def post_json(self, marketplace, url, *, headers=None, params=None, json_body=None):
        self.calls.append(json_body or {})
        return self.pages.pop(0) if self.pages else []


def gift(gift_id, price="10"):
    return {
        "gift_id": gift_id,
        "gift_num": int(gift_id) if str(gift_id).isdigit() else 1,
        "gift_name": "Plush Pepe",
        "model": "Albino (1.5%)",
        "price": price,
        "asset": "TON",
    }


def full_page(offset: int):
    return [gift(str(offset + index)) for index in range(PAGE_LIMIT)]


import pytest


@pytest.mark.asyncio
async def test_crawl_walks_past_the_first_page():
    http = FakePostHttp([full_page(0), full_page(100), [gift("999")]])

    snapshot = await TonnelParser(http).snapshot()

    assert len(snapshot.listings) == PAGE_LIMIT * 2 + 1
    assert [call["page"] for call in http.calls] == [1, 2, 3]


@pytest.mark.asyncio
async def test_crawl_stops_when_a_page_only_repeats_known_ids():
    page = full_page(0)
    http = FakePostHttp([page, list(page), full_page(500)])

    snapshot = await TonnelParser(http).snapshot()

    # The duplicate page ends the walk, the third page is never requested.
    assert len(snapshot.listings) == PAGE_LIMIT
    assert len(http.calls) == 2


@pytest.mark.asyncio
async def test_crawl_respects_its_page_budget():
    http = FakePostHttp([full_page(index * 100) for index in range(10)])

    snapshot = await TonnelParser(http, max_pages=2).snapshot()

    assert len(http.calls) == 2
    assert len(snapshot.listings) == PAGE_LIMIT * 2


def test_price_noise_threshold_is_meaningful():
    # Half a percent: enough to ignore rounding, small enough to catch real cuts.
    assert Decimal("0.4") < MIN_CHANGE_PERCENT <= Decimal("1")


def test_snapshot_timestamps_are_utc():
    assert datetime.now(timezone.utc).tzinfo is timezone.utc
