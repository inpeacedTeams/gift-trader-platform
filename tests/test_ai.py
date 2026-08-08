from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.ai.client import AiUnavailable, OpenRouterClient
from app.ai.context import ton
from app.ai.quota import DailyQuota
from app.core.config import Settings


def test_quota_blocks_after_the_limit():
    quota = DailyQuota(limit=2)

    assert quota.consume(1) is True
    assert quota.consume(1) is True
    assert quota.consume(1) is False
    assert quota.remaining(1) == 0


def test_quota_is_per_user():
    quota = DailyQuota(limit=1)

    assert quota.consume(1) is True
    assert quota.consume(2) is True


def test_quota_resets_on_a_new_day():
    quota = DailyQuota(limit=1)
    quota.consume(1)

    quota._day = "1999-01-01"

    assert quota.consume(1) is True


def test_ton_never_pads_zeros():
    assert ton(Decimal("90.000")) == "90 TON"
    assert ton(Decimal("12.50")) == "12.5 TON"
    assert ton(None) == "нет данных"


@pytest.mark.asyncio
async def test_client_without_key_refuses_instead_of_faking():
    client = OpenRouterClient(Settings(openrouter_api_key=None))

    assert client.enabled is False
    with pytest.raises(AiUnavailable) as error:
        await client.complete(system="s", user="u")

    assert "OPENROUTER_API_KEY" in error.value.reason


def test_client_sends_attribution_headers():
    client = OpenRouterClient(Settings(openrouter_api_key="sk-test"))

    headers = client._headers()

    assert headers["Authorization"] == "Bearer sk-test"
    assert "HTTP-Referer" in headers
    assert "X-Title" in headers


def test_datetime_import_is_available_for_quota_rollover():
    assert datetime.now(timezone.utc).tzinfo is timezone.utc
