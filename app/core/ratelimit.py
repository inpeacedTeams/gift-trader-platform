"""Token bucket rate limiting.

A bucket refills continuously, so a client can burst briefly and then
settles into a steady rate. Fixed windows would let someone fire a whole
window of requests at the boundary and do it again a second later.

State lives in this process. That is enough for one instance; a second
worker doubles the effective allowance, so move this to Redis before
scaling out horizontally.
"""

import time
from dataclasses import dataclass, field


@dataclass
class Bucket:
    tokens: float
    updated_at: float


@dataclass
class TokenBucket:
    rate_per_minute: int
    burst: int
    _buckets: dict[str, Bucket] = field(default_factory=dict)

    def _refill_rate(self) -> float:
        return self.rate_per_minute / 60.0

    def take(self, key: str) -> tuple[bool, int, float]:
        """Spend one token.

        Returns whether it was allowed, how many remain, and how long to
        wait before the next one is available.
        """
        now = time.monotonic()
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = Bucket(tokens=float(self.burst), updated_at=now)
            self._buckets[key] = bucket
        elapsed = now - bucket.updated_at
        bucket.tokens = min(self.burst, bucket.tokens + elapsed * self._refill_rate())
        bucket.updated_at = now
        if bucket.tokens < 1:
            retry_after = (1 - bucket.tokens) / self._refill_rate()
            return False, 0, retry_after
        bucket.tokens -= 1
        return True, int(bucket.tokens), 0.0

    def prune(self, max_idle_seconds: float = 900) -> None:
        """Drop buckets nobody has touched, so memory does not grow forever."""
        cutoff = time.monotonic() - max_idle_seconds
        for key in [key for key, item in self._buckets.items() if item.updated_at < cutoff]:
            del self._buckets[key]
