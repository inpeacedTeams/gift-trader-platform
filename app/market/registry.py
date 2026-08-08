from collections.abc import Callable

from app.core.config import Settings, get_settings

from .base import MarketParser
from .fragment import FragmentParser
from .getgems import GetGemsParser
from .http import MarketHttp
from .portals import PortalsParser
from .tonnel import TonnelParser


def build_parsers(
    *,
    getgems_collections: list[str] | None = None,
    portals_endpoint: str | None = None,
    settings: Settings | None = None,
) -> list[MarketParser]:
    settings = settings or get_settings()
    collections = (
        getgems_collections
        if getgems_collections is not None
        else settings.getgems_collection_list
    )
    http = MarketHttp(
        timeout=settings.source_timeout_seconds,
        retries=settings.source_retries,
        backoff_seconds=settings.source_backoff_seconds,
    )
    builders: dict[str, Callable[[], MarketParser]] = {
        "tonnel": lambda: TonnelParser(
            http, settings.tonnel_endpoint, max_pages=settings.crawl_max_pages
        ),
        "getgems": lambda: GetGemsParser(
            http,
            collections,
            settings.tonapi_base_url,
            api_token=settings.tonapi_token,
            max_pages=settings.crawl_max_pages,
        ),
        "portals": lambda: PortalsParser(
            http,
            portals_endpoint or settings.portals_endpoint,
            auth_data=settings.portals_auth_data,
        ),
        "fragment": lambda: FragmentParser(http),
    }
    return [builders[name]() for name in settings.market_source_list if name in builders]
