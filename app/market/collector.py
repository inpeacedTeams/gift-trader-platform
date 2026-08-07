import asyncio
from dataclasses import dataclass

from .base import MarketParser
from .models import MarketSnapshot, SourceUnavailable


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

    results = await asyncio.gather(*(run(parser) for parser in parsers))
    snapshots = [result for result in results if isinstance(result, MarketSnapshot)]
    unavailable = [
        {"marketplace": result.marketplace, "reason": result.reason}
        for result in results
        if isinstance(result, SourceUnavailable)
    ]
    return CollectorResult(snapshots=snapshots, unavailable=unavailable)
