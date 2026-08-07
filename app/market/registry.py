from .base import MarketParser
from .fragment import FragmentParser
from .getgems import GetGemsParser
from .http import MarketHttp
from .portals import PortalsParser


def build_parsers(*, getgems_collections: list[str], portals_endpoint: str = "https://portal-market.com/api") -> list[MarketParser]:
    http = MarketHttp()
    return [
        FragmentParser(http),
        PortalsParser(http, portals_endpoint),
        GetGemsParser(http, getgems_collections),
    ]
