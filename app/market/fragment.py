import re
from datetime import datetime, timezone
from decimal import Decimal

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from .base import MarketParser
from .http import MarketHttp
from .models import Listing, MarketSnapshot, SourceUnavailable


class FragmentParser(MarketParser):
    marketplace = "fragment"

    def __init__(self, http: MarketHttp, url: str = "https://fragment.com/gifts"):
        self.http = http
        self.url = url

    async def snapshot(self) -> MarketSnapshot:
        now = datetime.now(timezone.utc)
        html = await self.http.get_text(
            "fragment", self.url, headers={"Accept": "text/html"}
        )
        soup = BeautifulSoup(html, "html.parser")
        listings: list[Listing] = []
        for node in soup.select("[data-price], .tm-grid-item, .tm-gift-item"):
            raw_price = node.get("data-price") or node.select_one("[data-price]")
            if not raw_price:
                continue
            raw_price = (
                raw_price if isinstance(raw_price, str) else raw_price.get("data-price")
            )
            match = re.search(r"[0-9]+(?:[.,][0-9]+)?", str(raw_price))
            if not match:
                continue
            link = node if node.name == "a" else node.select_one("a[href]")
            href = link.get("href") if link else None
            if not href:
                continue
            absolute = href if href.startswith("http") else f"https://fragment.com{href}"
            price = Decimal(match.group().replace(",", "."))
            if price <= 0:
                continue
            listings.append(
                Listing(
                    marketplace="fragment",
                    listing_id=absolute,
                    gift_id=absolute,
                    name=node.get("data-name") or node.get_text(" ", strip=True)[:120],
                    price_ton=price,
                    url=HttpUrl(absolute),
                    observed_at=now,
                    source_url=HttpUrl(self.url),
                )
            )
        if not listings:
            raise SourceUnavailable(
                "fragment",
                f"no listings parsed from {self.url}: page layout changed or content is rendered client side",
            )
        return MarketSnapshot(
            marketplace="fragment",
            observed_at=now,
            listings=listings,
            source_url=HttpUrl(self.url),
        )
