from decimal import Decimal
from types import SimpleNamespace

from app.notifications.alerts import GiftAlertEvaluator
from app.notifications.portfolio_alerts import portfolio_message


def rule(rule_type: str, threshold: str, gift_id: int | None = 1):
    return SimpleNamespace(
        id=1, user_id=1, gift_id=gift_id, rule_type=rule_type, threshold=Decimal(threshold)
    )


def snapshot(floor="180", previous="210"):
    return {
        "name": "Plush Pepe",
        "model": "Albino",
        "collection": "Plush Pepes",
        "floor": Decimal(floor),
        "marketplace": "tonnel",
        "url": "https://t.me/nft/PlushPepe-834",
        "previous": Decimal(previous) if previous else None,
    }


def message(rule_type, threshold, **kwargs):
    evaluator = GiftAlertEvaluator(session=None)
    return evaluator._message(rule(rule_type, threshold), snapshot(**kwargs))


def test_price_below_fires_under_the_threshold():
    text = message("price_below", "190")

    assert text is not None
    assert "Plush Pepe · Albino" in text
    assert "180 TON на tonnel" in text
    assert "ниже 190 TON" in text
    assert "https://t.me/nft/PlushPepe-834" in text


def test_price_below_stays_quiet_above_the_threshold():
    assert message("price_below", "150") is None


def test_price_above_fires_over_the_threshold():
    text = message("price_above", "150")

    assert text is not None
    assert "выше 150 TON" in text


def test_change_percent_uses_the_previous_floor():
    text = message("change_percent", "10")

    # 210 -> 180 is a 14 percent drop, past a 10 percent rule.
    assert text is not None
    assert "-14.3%" in text


def test_change_percent_needs_a_previous_floor():
    assert message("change_percent", "10", previous=None) is None


def test_small_moves_do_not_fire_a_percent_rule():
    assert message("change_percent", "25") is None


def test_portfolio_message_is_readable():
    text = portfolio_message(
        "portfolio_value_below", Decimal("1240.5"), Decimal("-8.3"), Decimal("1300")
    )

    assert "Портфель ниже порога" in text
    assert "1240.5 TON" in text
    assert "-8.30%" in text
    # The raw rule type must never reach the user.
    assert "portfolio_value_below" not in text
