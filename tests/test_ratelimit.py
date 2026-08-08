import time

from app.core.ratelimit import TokenBucket


def test_burst_is_allowed_then_blocked():
    bucket = TokenBucket(rate_per_minute=60, burst=3)

    assert [bucket.take("a")[0] for _ in range(3)] == [True, True, True]
    allowed, remaining, retry_after = bucket.take("a")

    assert allowed is False
    assert remaining == 0
    assert retry_after > 0


def test_clients_have_separate_buckets():
    bucket = TokenBucket(rate_per_minute=60, burst=1)

    assert bucket.take("a")[0] is True
    assert bucket.take("a")[0] is False
    assert bucket.take("b")[0] is True


def test_tokens_refill_over_time(monkeypatch):
    bucket = TokenBucket(rate_per_minute=600, burst=1)
    clock = {"now": 1000.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["now"])

    assert bucket.take("a")[0] is True
    assert bucket.take("a")[0] is False

    # 600 per minute is ten per second, so a fifth of a second is two tokens.
    clock["now"] += 0.2
    assert bucket.take("a")[0] is True


def test_refill_never_exceeds_the_burst(monkeypatch):
    bucket = TokenBucket(rate_per_minute=60, burst=2)
    clock = {"now": 1000.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["now"])
    bucket.take("a")

    clock["now"] += 3600

    assert bucket.take("a")[0] is True
    assert bucket.take("a")[0] is True
    assert bucket.take("a")[0] is False


def test_idle_buckets_are_pruned(monkeypatch):
    bucket = TokenBucket(rate_per_minute=60, burst=1)
    clock = {"now": 1000.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["now"])
    bucket.take("a")

    clock["now"] += 1000
    bucket.prune(max_idle_seconds=900)

    assert "a" not in bucket._buckets
