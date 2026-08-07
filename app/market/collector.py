import asyncio
from dataclasses import dataclass
import logging
from .base import MarketParser
from .models import MarketSnapshot, SourceUnavailable

logger = logging.getLogger(__name__)

@dataclass
class CollectorResult:
    snapshots: list[MarketSnapshot]
    unavailable: list[dict[str, str]]

async def collect(parsers: list[MarketParser]) -> CollectorResult:
    async def run(parser: MarketParser):
        try:
            return await parser.snapshot()
        except SourceUnavailable as exc:
            return exc
        except Exception as exc:
            logger.exception("Unexpected collector failure", extra={"marketplace": parser.marketplace})
            return SourceUnavailable(parser.marketplace, f"unexpected parser failure: {exc}")

    results = await asyncio.gather(*(run(parser) for parser in parsers))
    snapshots = [result for result in results if isinstance(result, MarketSnapshot)]
    unavailable = [{"marketplace": result.marketplace, "reason": result.reason} for result in results if isinstance(result, SourceUnavailable)]
    return CollectorResult(snapshots=snapshots, unavailable=unavailable)
