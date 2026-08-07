from decimal import Decimal
from datetime import datetime, timezone
from app.portfolio.sync import _evaluate_alerts

async def test_portfolio_alert_requires_previous_valuation(db_session, user, portfolio_valuation_factory, alert_rule_factory):
    current = await portfolio_valuation_factory(user.id, Decimal("120"))
    await alert_rule_factory(user.id, "portfolio_value_above", Decimal("100"))
    assert await _evaluate_alerts(db_session, user.id, current) == 0

async def test_portfolio_alert_triggers_once_per_window(db_session, user, portfolio_valuation_factory, alert_rule_factory):
    previous = await portfolio_valuation_factory(user.id, Decimal("100"))
    current = await portfolio_valuation_factory(user.id, Decimal("120"))
    await alert_rule_factory(user.id, "portfolio_change_percent", Decimal("10"))
    assert await _evaluate_alerts(db_session, user.id, current) == 1
    await db_session.commit()
    assert await _evaluate_alerts(db_session, user.id, current) == 0
