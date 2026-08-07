from datetime import datetime, timezone
import pytest
from app.market.collector import collect
from app.market.models import MarketSnapshot, SourceUnavailable

class HealthyParser:
    marketplace = "healthy"
    async def snapshot(self):
        now = datetime.now(timezone.utc)
        return MarketSnapshot(marketplace="fragment", observed_at=now, listings=[], source_url="https://fragment.com")

class BrokenParser:
    marketplace = "broken"
    async def snapshot(self):
        raise RuntimeError("provider changed")

@pytest.mark.asyncio
async def test_one_source_failure_does_not_drop_other_sources():
    result = await collect([HealthyParser(), BrokenParser()])
    assert len(result.snapshots) == 1
    assert result.snapshots[0].marketplace == "fragment"
    assert result.unavailable == [{"marketplace": "broken", "reason": "unexpected parser failure: provider changed"}]
