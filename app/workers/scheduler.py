import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

class MarketScheduler:
    def __init__(self, job: Callable[[], Awaitable[object]], interval_seconds: int):
        self.job = job
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self.job()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("scheduled market sync failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue

    async def start(self) -> None:
        if self._task is None:
            self._stop.clear()
            self._task = asyncio.create_task(self._loop(), name="gift-trader-market-sync")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
