from app.ai.prompts import CHAT_SYSTEM, GROUNDING, VERDICT_SYSTEM
from app.core.config import Settings


def test_prompts_forbid_inventing_numbers():
    assert "Never invent a price" in GROUNDING
    assert GROUNDING in CHAT_SYSTEM
    assert GROUNDING in VERDICT_SYSTEM


def test_verdict_prompt_asks_for_three_parts():
    for label in ("Read:", "Risk:", "Call:"):
        assert label in VERDICT_SYSTEM


def test_assistant_is_off_until_a_key_is_present():
    from app.ai.client import OpenRouterClient

    assert OpenRouterClient(Settings(openrouter_api_key=None)).configured is False
    assert OpenRouterClient(Settings(openrouter_api_key="sk-or-test")).configured is True


def test_default_model_costs_nothing():
    assert Settings().openrouter_model == "openrouter/free"


def test_rate_limiter_blocks_after_the_limit():
    from app.ai.limits import RateLimiter

    limiter = RateLimiter(limit=2)

    assert limiter.check(1)[0] is True
    assert limiter.check(1)[0] is True
    assert limiter.check(1) == (False, 0)
    # A different user has their own budget.
    assert limiter.check(2)[0] is True


def test_ttl_cache_returns_stored_values():
    from app.ai.limits import TTLCache

    cache = TTLCache(ttl_seconds=60)
    cache.set("7", "verdict")

    assert cache.get("7") == "verdict"
    assert cache.get("8") is None
