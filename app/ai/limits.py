import time
from collections import defaultdict, deque


class RateLimiter:
    """Per user sliding window.

    The OpenRouter key is ours, so one enthusiastic user must not be able to
    drain the shared quota for everyone else.
    """

    def __init__(self, limit: int, window_seconds: int = 3600):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[int, deque[float]] = defaultdict(deque)

    def allow(self, user_id: int) -> bool:
        now = time.monotonic()
        hits = self._hits[user_id]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True

    def remaining(self, user_id: int) -> int:
        return max(0, self.limit - len(self._hits[user_id]))
