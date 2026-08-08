import time
from collections import defaultdict, deque


class RateLimiter:
    """Per user sliding window.

    The OpenRouter key is ours, so an unbounded endpoint is an unbounded
    bill. In memory is enough for a single instance; move to Redis when the
    API runs on more than one process.
    """

    def __init__(self, limit: int, window_seconds: int = 3600):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[int, deque[float]] = defaultdict(deque)

    def _prune(self, user_id: int) -> deque[float]:
        now = time.monotonic()
        hits = self._hits[user_id]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        return hits

    def remaining(self, user_id: int) -> int:
        return max(0, self.limit - len(self._prune(user_id)))

    def allow(self, user_id: int) -> bool:
        """Records a call and reports whether it was within the quota."""
        hits = self._prune(user_id)
        if len(hits) >= self.limit:
            return False
        hits.append(time.monotonic())
        return True


class TTLCache:
    """Tiny time based cache so repeated views do not re-bill the same answer."""

    def __init__(self, ttl_seconds: int):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        stored_at, value = entry
        if time.monotonic() - stored_at > self.ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: str) -> None:
        self._store[key] = (time.monotonic(), value)
