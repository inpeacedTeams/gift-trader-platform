import pytest

from app.ai.limits import RateLimiter, TTLCache
from app.ai.prompts import CHAT_SYSTEM, VERDICT_SYSTEM


def test_rate_limiter_blocks_after_the_quota():
    limiter = RateLimiter(limit=2)

    assert limiter.allow(1) is True
    assert limiter.allow(1) is True
    assert limiter.allow(1) is False
    # A different user has their own budget.
    assert limiter.allow(2) is True


def test_rate_limiter_reports_remaining():
    limiter = RateLimiter(limit=3)
    limiter.allow(7)

    assert limiter.remaining(7) == 2
    assert limiter.remaining(99) == 3


def test_ttl_cache_returns_stored_values():
    cache = TTLCache(ttl_seconds=60)
    cache.set("12", "verdict")

    assert cache.get("12") == "verdict"
    assert cache.get("13") is None


def test_ttl_cache_expires():
    cache = TTLCache(ttl_seconds=0)
    cache.set("12", "verdict")

    assert cache.get("12") is None


@pytest.mark.parametrize("prompt", [CHAT_SYSTEM, VERDICT_SYSTEM])
def test_prompts_forbid_inventing_data(prompt):
    lowered = prompt.lower()

    assert "never invent" in lowered
    assert "data" in lowered
