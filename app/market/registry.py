from app.core.config import Settings, get_settings
from .base import MarketParser
from .fragment import FragmentParser
from .getgems import GetGemsParser
from .http import MarketHttp
from .portals import PortalsParser


def build_parsers(*, getgems_collections: list[str], portals_endpoint: str | None = None, settings: Settings | None = None) -> list[MarketParser]:
    settings = settings or get_settings()
    http = MarketHttp(timeout=settings.source_timeout_seconds, retries=settings.source_retries, backoff_seconds=settings.source_backoff_seconds)
    return [
        FragmentParser(http),
        PortalsParser(http, portals_endpoint or settings.portals_endpoint),
        GetGemsParser(http, getgems_collections, settings.tonapi_base_url),
    ]
