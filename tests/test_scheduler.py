import asyncio
import pytest
from app.workers.scheduler import MarketScheduler

@pytest.mark.asyncio
async def test_scheduler_runs_job_and_stops():
    calls = 0
    async def job():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
    scheduler = MarketScheduler(job, interval_seconds=60)
    await scheduler.start()
    await asyncio.sleep(0.02)
    await scheduler.stop()
    assert calls >= 1
    assert scheduler._task is None
